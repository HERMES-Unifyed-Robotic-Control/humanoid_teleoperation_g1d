# G1-D 直接集成说明

本项目已经把修改合入 `teleop/` 源码，无需再改机器人自带的 `/unitree/module/unitree_eai/xr_teleoperate`。

## 已合入的控制修改

- `teleop/utils/instruction_map.py`：每个主循环只采一次手柄数据；左 Y 映射底盘前后、左 X 映射底盘旋转、右 Y 映射升降、右 X 映射腰部俯仰。
- `teleop/robot_control/robot_arm.py`：`--use-waist` 控制 `WaistPitch=14`；G1-D 不存在的 `WaistRoll=13` 不参与控制，`WaistYaw=12` 不再被右摇杆占用。
- `teleop/robot_control/robot_arm_ik.py`：直接加载 `assets/g1_D/g1_d.urdf`，缓存文件为 `teleop/g1d_arm_model_cache.pkl`，不再复用普通 G1 的 URDF 或旧缓存。
- `teleop/teleop_hand_and_arm.py`：同一个 `tele_data` 样本同时供双臂 IK、底盘、升降、腰部和 EpisodeWriter 使用，并把原始 XR 输入与实际控制目标写入 episode。

腰部 Pitch 位置限制为约 `-2.5°～135°`，右摇杆经死区和平滑曲线后每帧最多改变 `0.01 rad`。低层 Pitch 增益使用最新 G1-D SDK2 示例中的 `kp=40, kd=1`。

## EpisodeWriter 新字段

每帧额外保存 `states.xr` 和 `actions.operator`。EpisodeWriter 原生递归序列化字典，RerunLogger 也会递归展开其中的数值，因此这些字段不会改变已有左右臂、Dex1、底盘、升降和相机字段。

Trigger 在 `states.xr` 和 `actions.operator.dex1` 中统一为 `0=全开、1=全闭`。`left_ee/right_ee` 中仍保留真正发布给 Dex1 服务的电机目标以及返回状态。

切换到 `bridge/g1d_agv_bridge.cpp` 时，需要停止 `G1_Mobile_Lift_Controller` 的发布端。两个后端控制相同的 DDS 目标，不能同时运行。
