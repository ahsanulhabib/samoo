from frameworks.factory import Framework
import numpy as np
from metamodels.model_selection import prepare_data
from itertools import product


class Framework11(Framework):
    def __init__(self,
                 framework_id=None,
                 problem=None,
                 algorithm=None,
                 ref_dirs=None,
                 model_list=None,
                 curr_ref_id=None,
                 f_aggregate_func='asf',
                 *args,
                 **kwargs
                 ):
        super().__init__(framework_id=framework_id,
                         problem=problem,
                         algorithm=algorithm,
                         model_list=model_list,
                         ref_dirs=ref_dirs,
                         curr_ref_id=curr_ref_id,
                         f_aggregate_func=f_aggregate_func,
                         *args,
                         **kwargs)
        self.type = 1

    def train(self, x, f, g, *args, **kwargs):
        for i in range(0, self.problem.n_obj):
            self.model_list["f"+str(i+1)].train(x, f[:, i])

        if self.problem.n_constr > 0:
            for i in range(0, self.problem.n_constr):
                self.model_list["g"+str(i+1)].train(x, g[:, i])

    def predict(self, x, out, *args, **kwargs):
        f = []
        g = []
        for i in range(0, self.problem.n_obj):
            _f = self.model_list["f" + str(i + 1)].predict(x)
            f.append(_f)
        if self.problem.n_constr > 0:
            for i in range(0, self.problem.n_constr):
                _g = self.model_list["g" + str(i + 1)].predict(x)
                g.append(_g)
        else:
            _g = np.zeros(x.shape[0])
            g.append(_g)

        F = np.column_stack(f)
        G = np.column_stack(g)
        d = prepare_data(f=F,
                         g=g,
                         acq_func=['l_'+self.f_aggregate_func],
                         ref_dirs=self.ref_dirs,
                         curr_ref_id=self.curr_ref_id)
        out["F"] = d['l_'+self.f_aggregate_func]
        out["G"] = G

    def calculate_sep(self, problem, actual_data, prediction_data, n_split):

        err = []
        for partition in range(n_split):
            I_temp = np.arange(0, actual_data['f1'][partition].shape[0])
            I = np.asarray(list(product(I_temp, I_temp)))
            # find cv for the current partition
            if problem.n_constr > 0:
                g = []
                g_pred = []
                for j in range(problem.n_constr):
                    g.append(actual_data['g' + str(j + 1)][partition])
                    g_pred.append(prediction_data['g' + str(j + 1)][partition])

                g = np.column_stack(g)
                g_pred = np.column_stack(g_pred)

                cv = np.copy(g)
                cv[g <= 0] = 0
                cv = np.sum(cv, axis=1)

                cv_pred = np.copy(g_pred)
                cv_pred[g_pred <= 0] = 0
                cv_pred = np.sum(cv_pred, axis=1)
            else:
                cv = np.zeros([I_temp.shape[0], 1])
                cv_pred = np.zeros([I_temp.shape[0], 1])

            # objective values for the current partition
            f = []
            f_pred = []
            for i in range(problem.n_obj):
                f.append(actual_data['f'+str(i+1)][partition])
                f_pred.append(prediction_data['f' + str(i + 1)][partition])

            F = np.column_stack(f)
            F_pred = np.column_stack(f_pred)
            # compute average error over all reference directions
            temp_err = 0
            count = 0
            for j in range(self.ref_dirs.shape[0]):

                d = prepare_data(f=F, acq_func=['l_'+self.f_aggregate_func], ref_dirs=self.ref_dirs,
                                                curr_ref_id=j)

                f = d['l_'+self.f_aggregate_func]

                d = prepare_data(f=F_pred, acq_func=['l_'+self.f_aggregate_func], ref_dirs=self.ref_dirs,
                                                curr_ref_id=j)
                f_pred = d['l_'+self.f_aggregate_func]

                for i in range(I.shape[0]):
                    count = count + 1
                    d1 = self.constrained_domination(f[I[i, 0]], f[I[i, 1]], cv[I[i, 0]], cv[I[i, 1]])
                    d2 = self.constrained_domination(f_pred[I[i, 0]], f_pred[I[i, 1]], cv_pred[I[i, 0]], cv_pred[I[i, 1]])
                    if d1 != d2:
                        temp_err = temp_err + 1
            temp_err = temp_err/count
            err.append(temp_err)

        return np.asarray(err)
