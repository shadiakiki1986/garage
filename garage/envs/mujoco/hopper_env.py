import numpy as np

from garage.core import Serializable
from garage.envs import Step
from garage.envs.mujoco import MujocoEnv
from garage.logger import tabular
from garage.misc import autoargs
from garage.misc.overrides import overrides

# states: [
# 0: z-coord,
# 1: x-coord (forward distance),
# 2: forward pitch along y-axis,
# 6: z-vel (up = +),
# 7: xvel (forward = +)


class HopperEnv(MujocoEnv, Serializable):

    FILE = 'hopper.xml'

    @autoargs.arg(
        'alive_coeff', type=float, help='reward coefficient for being alive')
    @autoargs.arg(
        'ctrl_cost_coeff', type=float, help='cost coefficient for controls')
    def __init__(self, alive_coeff=1, ctrl_cost_coeff=0.01, *args, **kwargs):
        self.alive_coeff = alive_coeff
        self.ctrl_cost_coeff = ctrl_cost_coeff

        super().__init__(*args, **kwargs)

        # Always call Serializable constructor last
        Serializable.quick_init(self, locals())

    @overrides
    def get_current_obs(self):
        return np.concatenate([
            self.sim.data.qpos[0:1].flat,
            self.sim.data.qpos[2:].flat,
            np.clip(self.sim.data.qvel, -10, 10).flat,
            np.clip(self.sim.data.qfrc_constraint, -10, 10).flat,
            self.get_body_com("torso").flat,
        ])

    @overrides
    def step(self, action):
        self.forward_dynamics(action)
        next_obs = self.get_current_obs()
        lb, ub = self.action_bounds
        scaling = (ub - lb) * 0.5
        vel = self.get_body_comvel("torso")[0]
        reward = vel + self.alive_coeff - \
            0.5 * self.ctrl_cost_coeff * np.sum(np.square(action / scaling))
        state = self._state
        notdone = np.isfinite(state).all() and \
            (np.abs(state[3:]) < 100).all() and (state[0] > .7) and \
            (abs(state[2]) < .2)
        done = not notdone
        return Step(next_obs, reward, done)

    @overrides
    def log_diagnostics(self, paths):
        progs = [
            path["observations"][-1][-3] - path["observations"][0][-3]
            for path in paths
        ]
        tabular.record('AverageForwardProgress', np.mean(progs))
        tabular.record('MaxForwardProgress', np.max(progs))
        tabular.record('MinForwardProgress', np.min(progs))
        tabular.record('StdForwardProgress', np.std(progs))
