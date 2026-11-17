# AGENTS.md

Guidance for AI coding agents working in this repository (OpenVINS — filter-based visual-inertial estimation). Assumes a Linux host.

## Repo layout

Five catkin/ament packages, no root build file:

- `ov_core/` — shared library: camera models, feature extraction/tracking (KLT + descriptor), JPL quaternion math, the type system for filter states, OpenCV YAML config parser (`ov_core/src/utils/opencv_yaml_parse.h`).
- `ov_init/` — static and dynamic initialization; dynamic MLE refinement built on Ceres.
- `ov_msckf/` — the estimator itself: `VioManager` orchestrates tracking → initialization → propagation (`state/Propagator`) → updates (`update/Updater{MSCKF,SLAM,ZeroVelocity}`); `sim/Simulator` generates synthetic IMU+camera data; `src/ros/ROS{1,2}Visualizer.cpp` subscribe/publish.
- `ov_eval/` — offline evaluation binaries (ATE/RPE/NEES, timing, format conversion) + `pose_to_file` recorder.
- `ov_data/` — simulation trajectories and dataset info; not compiled code.
- `config/` — one directory per platform (`rpng_sim`, `euroc_mav`, `rs_d455`, ...). Each contains `estimator_config.yaml` plus Kalibr-style `kalibr_imu_chain.yaml` / `kalibr_imucam_chain.yaml`.

Shared cmake target logic lives in each package's `cmake/ROS1.cmake` and `cmake/ROS2.cmake`; the ROS-free build also uses `ROS1.cmake` with `ROS_AVAILABLE=0`. When adding/removing sources or executables, edit the correct `cmake/*.cmake` — source lists are explicit there (only a few globs).

## Builds

No root `CMakeLists.txt`; each package configures standalone. Dependencies: Eigen3, OpenCV 3 or 4, Boost (system, filesystem, thread, date_time), Ceres (needed by `ov_msckf` and `ov_init`). C++17 (required by ROS 2 Jazzy). The OpenCV version must match the one `cv_bridge` was built against, otherwise runtime segfaults — this is why the CI images pin distro-specific OpenCV.

Useful options (all packages): `-DENABLE_ROS=OFF` forces the ROS-free build even when ROS is installed. `ov_msckf`: `-DENABLE_ARUCO_TAGS=OFF` if OpenCV contrib is unavailable. `ov_eval`: `-DDISABLE_MATPLOTLIB=ON` skips the optional Python/matplotlib bindings. Note: the documented `BUILD_OV_EVAL` option does not exist in the current CMake files; ignore it.

ROS-free (what CI `build.yml` does — compiles `ov_core` + `ov_init` + `ov_msckf` together, excluding their standalone test binaries):

```sh
mkdir build && cd build
cmake ../ov_msckf/
make
```

ROS 1 (from a catkin workspace with this repo under `src/`):

```sh
catkin build
source devel/setup.bash
roslaunch ov_msckf simulation.launch verbosity:=WARNING
```

ROS 2 (from a colcon workspace with this repo under `src/`):

```sh
colcon build
source install/setup.bash
ros2 run ov_msckf run_simulation src/open_vins/config/rpng_sim/estimator_config.yaml
```

For ROS 2 Jazzy (Ubuntu 24.04) there is also a launch-file interface mirroring the ROS 1 one:

```sh
ros2 launch ov_msckf simulation.launch.py config:=rpng_sim
```

If both ROS 1 and ROS 2 are visible in the environment, CMake prefers ROS 1. Seven root `Dockerfile_ros{1,2}_*` images reproduce each supported Ubuntu/ROS combination (including Jazzy via `Dockerfile_ros2_24_04`); CI (`.github/workflows/`) builds all of them and runs the simulation as the smoke test.

## Tests

There is no CTest integration. "Tests" are plain executables that must be run manually with a config path:

```sh
./test_sim_repeat <path/to/estimator_config.yaml>   # replays sim twice, asserts identical measurements
./test_sim_meas  <config>                           # simulation + filter, records NEES/RMSE
./test_dynamic_init <config>                        # ov_init dynamic initializer
```

Expect long runtimes (minutes) — they simulate a full trajectory. When editing `sim/`, `test_sim_repeat` is the focused repeatability check; its asserts only fire in debug builds. Verbosity is controlled by the `verbosity` key in the config (`ALL, DEBUG, INFO, WARNING, ERROR, SILENT`).

## Configuration quirks

- Estimator configs are OpenCV `FileStorage` YAML, not standard YAML — first line must be `%YAML:1.0`. Values look like `key: value` with typed quoting; keep the format when editing.
- Configs are split across three files per platform dir: `estimator_config.yaml`, `kalibr_imu_chain.yaml`, `kalibr_imucam_chain.yaml`, referenced from the estimator config via `relative_config_imu` / `relative_config_imucam` (resolved relative to the config file's directory). Adding a parameter means touching both the YAML and the parser (e.g. `VioManagerOptions::print_and_load`).
- `YamlParser` treats unset-but-requested parameters as errors: after parsing, `parser->successful()` must be true or the binary exits. If you add a config option, provide a default.
- `sim_traj_path` in `rpng_sim/estimator_config.yaml` is relative to the *launch* working directory (`src/open_vins/ov_data/sim/...`), which only works inside a ROS workspace. For ROS-free runs, pass an absolute path or run from a directory where that prefix resolves.
- ROS params override YAML: in ROS 1 the launch file sets `config_path` plus many overrides; in ROS 2 overrides come from the command line. Keep launch files and YAML in sync when renaming keys.

## Code conventions

- Format: `./run_format.sh` (clang-format, `.clang-format` at root, LLVM-based, 2-space). Run it before committing; CI does not check it.
- Every source file carries the GPL-3 header; new files should include it (see any existing file). `./run_copyright.sh` rewrites headers in bulk — don't run it casually, it touches every file.
- Quaternions are JPL convention (x, y, z, w ordering), not Hamilton; rotations/transforms are named like `R_GtoI` / `q_ItoC`. Respect this in any math you add; helpers are in `ov_core/src/utils/quat_ops.h`.
- Logging goes through the `PRINT_*` macros (`ov_core/src/utils/print.h`), not raw printf/iostream; verbosity is runtime-configurable.
- `ROS_AVAILABLE` is a compile-time macro (0 = ROS-free, 1 = ROS 1, 2 = ROS 2). ROS-dependent code is `#if`-guarded on it; keep new code building in all three modes unless impossible.
- Release = tagged version bumps in all five `package.xml` files (currently 2.7.0). Keep them in sync.

## Docs

`docs/` holds Doxygen input (`*.dox`); the published docs are at https://docs.openvins.com/ . The `getting-started` and `simulation` pages explain config keys in detail — consult them before guessing at parameter semantics.
