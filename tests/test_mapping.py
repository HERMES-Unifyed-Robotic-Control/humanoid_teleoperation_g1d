import unittest
from types import SimpleNamespace

import numpy as np

from xr_teleoperate_g1d import ControlLimits, TeleopInput, map_input, xrobotoolkit_mapping
from xr_teleoperate_g1d.unitree_teleop_adapter import from_televuer
from teleop.utils.instruction_map import ControlDataMapper, HandleInstruction


class MappingTest(unittest.TestCase):
    def test_full_scale_mapping_and_gripper_clamp(self):
        frame = map_input(
            TeleopInput(
                left_y=1.0,
                left_x=-1.0,
                right_x=-1.0,
                right_y=1.0,
                left_trigger=-0.5,
                right_trigger=1.5,
                left_grip=1.0,
            )
        )
        self.assertEqual(frame["actions"]["chassis"], {"vx": -0.2, "vy": 0.0, "vyaw": 0.6})
        self.assertEqual(frame["actions"]["lift"]["vz"], -1.0)
        self.assertEqual(frame["actions"]["waist"]["pitch_velocity"], 0.3)
        self.assertEqual(frame["actions"]["dex1"]["left_closed_ratio"], 0.0)
        self.assertEqual(frame["actions"]["dex1"]["right_closed_ratio"], 1.0)
        self.assertTrue(frame["actions"]["arm"]["left_active"])

    def test_deadzone_and_tracking_loss_command_stop(self):
        within_deadzone = map_input(TeleopInput(left_y=0.05, right_x=0.05, right_y=0.05))
        self.assertEqual(within_deadzone["actions"]["chassis"]["vx"], 0.0)
        self.assertEqual(within_deadzone["actions"]["lift"]["vz"], 0.0)

        stopped = map_input(TeleopInput(motion_ready=False, left_y=1.0, right_x=1.0, right_y=1.0))
        self.assertEqual(stopped["actions"]["chassis"]["vx"], 0.0)
        self.assertEqual(stopped["actions"]["chassis"]["vyaw"], 0.0)
        self.assertEqual(stopped["actions"]["lift"]["vz"], 0.0)
        self.assertTrue(stopped["safety"]["stop_commanded"])
        self.assertFalse(stopped["actions"]["dex1"]["enabled"])

    def test_generic_xrobotoolkit_layout_remains_available(self):
        limits = ControlLimits(deadzone=0.0, max_vx=0.2, max_vyaw=0.6, max_lift=1.0)
        frame = xrobotoolkit_mapping(
            TeleopInput(left_x=1.0, left_y=1.0, right_x=0.0, right_y=1.0), limits=limits
        )
        self.assertEqual(frame["actions"]["chassis"]["vx"], 0.2)
        self.assertEqual(frame["actions"]["chassis"]["vyaw"], 0.0)
        self.assertEqual(frame["actions"]["lift"]["vz"], 1.0)

    def test_unitree_trigger_convention_is_normalized(self):
        sample = from_televuer(
            SimpleNamespace(
                motion_data_ready=True,
                left_ctrl_thumbstickValue=[0.1, 0.2],
                right_ctrl_thumbstickValue=[0.3, 0.4],
                left_ctrl_triggerValue=10.0,
                right_ctrl_triggerValue=0.0,
                left_ctrl_squeezeValue=0.25,
                right_ctrl_squeezeValue=0.75,
                right_ctrl_aButton=False,
                right_ctrl_bButton=True,
                left_ctrl_aButton=True,
                left_ctrl_bButton=False,
                left_wrist_pose=[1.0] * 7,
                right_wrist_pose=[2.0] * 7,
                head_pose=[3.0] * 7,
            )
        )
        self.assertEqual(sample.left_trigger, 0.0)
        self.assertEqual(sample.right_trigger, 1.0)
        self.assertEqual(sample.arm["left_wrist_pose"], [1.0] * 7)
        self.assertEqual(sample.headset_pose, [3.0] * 7)
        self.assertTrue(sample.buttons["X"])
        self.assertTrue(sample.buttons["B"])

    def test_official_axis_mapping_and_tracking_loss_stop(self):
        tele_data = SimpleNamespace(
            motion_data_ready=True,
            left_ctrl_thumbstickValue=[0.25, -0.5],
            right_ctrl_thumbstickValue=[-0.75, 1.0],
            right_ctrl_aButton=True,
            right_ctrl_bButton=False,
        )
        instructions = HandleInstruction(False, None, None).get_instruction(tele_data)
        self.assertEqual(
            instructions,
            {"lx": 0.5, "ly": -0.25, "rx": 0.75, "ry": -1.0, "rbutton_A": True, "rbutton_B": False},
        )

        tele_data.motion_data_ready = False
        stopped = HandleInstruction(False, None, None).get_instruction(tele_data)
        self.assertEqual([stopped[key] for key in ("lx", "ly", "rx", "ry")], [0.0] * 4)

    def test_waist_mapper_controls_pitch_with_g1d_limits(self):
        mapper = ControlDataMapper(current_waist_pitch=0.0)
        mapped = mapper.update(rx=1.0, current_waist_pitch=0.0)
        self.assertAlmostEqual(mapped["waist_pitch_pos"], 0.01)

        mapped = mapper.update(rx=1.0, current_waist_pitch=3.0)
        self.assertAlmostEqual(mapped["waist_pitch_pos"], float(np.deg2rad(135.0)))

        mapper.update(lx=1.0, ly=1.0, ry=1.0)
        mapper.stop_motion()
        stopped = mapper.update(lx=0.0, ly=0.0, ry=0.0)
        self.assertEqual(stopped["mobile_x_vel"], 0.0)
        self.assertEqual(stopped["mobile_yaw_vel"], 0.0)
        self.assertEqual(stopped["g1_height"], 0.0)


if __name__ == "__main__":
    unittest.main()
