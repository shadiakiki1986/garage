import numpy as np

from garage.core import Serializable
from garage.envs import Step
from garage.envs.mujoco import MujocoEnv
from garage.logger import tabular
from garage.misc import autoargs
from garage.misc.overrides import overrides


def smooth_abs(x, param):
    return np.sqrt(np.square(x) + np.square(param)) - param


class Walker2DEnv(MujocoEnv, Serializable):

    FILE = 'walker2d.xml'

    @autoargs.arg(
        'ctrl_cost_coeff', type=float, help='cost coefficient for controls')
    def __init__(self, ctrl_cost_coeff=1e-2, *args, **kwargs):
        self.ctrl_cost_coeff = ctrl_cost_coeff
        super().__init__(*args, **kwargs)

        # Always call Serializable constructor last
        Serializable.quick_init(self, locals())

    def get_current_obs(self):
        return np.concatenate([
            self.sim.data.qpos.flat,
            self.sim.data.qvel.flat,
            self.get_body_com("torso").flat,
        ])

    def step(self, action):
        self.forward_dynamics(action)
        next_obs = self.get_current_obs()
        action = np.clip(action, *self.action_bounds)
        lb, ub = self.action_bounds
        scaling = (ub - lb) * 0.5
        ctrl_cost = 0.5 * self.ctrl_cost_coeff * \
            np.sum(np.square(action / scaling))
        forward_reward = self.get_body_comvel("torso")[0]
        reward = forward_reward - ctrl_cost
        qpos = self.sim.data.qpos
        done = not (qpos[0] > 0.8 and qpos[0] < 2.0 and qpos[2] > -1.0
                    and qpos[2] < 1.0)
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
