"""
This is the main file to be run on the cluster.
Modify this to fit the experiment you intend to run.
"""
from BoRisk.exp_loop import exp_loop
import torch
from BoRisk.test_functions import function_picker

# Modify this and make sure it does what you want!

function_name = "covid"
num_samples = 27  # 10 for benchmarks and starting
num_fantasies = 10  # default 50
key_list = ["random"]
# this should be a list of bm algorithms corresponding to the keys. None if rhoKG
bm_alg_list = [None]
q_base = 1  # q for rhoKG. For others, it is q_base / num_samples
iterations = 200

# seed_list = [int(sys.argv[1])]
seed_list = range(1, 101)

output_file = "%s_%s" % (function_name, "cvar")
torch.manual_seed(0)  # to ensure the produced seed are same!
kwargs = dict()
dim_w = 3
kwargs["noise_std"] = None  # noise is built in to the simulator
function = function_picker(function_name)
w_samples = function.w_samples
weights = function.weights
kwargs["weights"] = weights
dim_x = function.dim - dim_w
num_restarts = 10 * function.dim
raw_multiplier = 50  # default 50

kwargs["num_inner_restarts"] = 5 * dim_x
kwargs["CVaR"] = True
kwargs["alpha"] = 0.9
kwargs["disc"] = True
num_x_samples = 6
num_init_w = 10

output_dict = dict()

for i, key in enumerate(key_list):
    if key not in output_dict.keys():
        output_dict[key] = dict()
    for seed in seed_list:
        seed = int(seed)
        print("starting key %s seed %d" % (key, seed))
        filename = output_file + "_" + key + "_" + str(seed)
        random = "random" in key
        apx = "apx" in key
        if "tts" in key:
            tts_frequency = 10
        else:
            tts_frequency = 1
        if num_x_samples:
            # constrained initialization - only uses the first constraint if exists
            old_state = torch.random.get_rng_state()
            torch.manual_seed(seed)
            x_samples = torch.rand(num_x_samples, dim_x)
            if function.inequality_constraints is not None:
                ineq = function.inequality_constraints[0]
                ineq_ind = ineq[0]
                ineq_coef = ineq[1]
                ineq_rhs = ineq[2]
                while True:
                    num_violated = torch.sum(
                        torch.sum(x_samples[..., ineq_ind] * ineq_coef, dim=-1)
                        < ineq_rhs
                    )
                    if num_violated == 0:
                        break
                    violated_ind = (
                        torch.sum(x_samples[..., ineq_ind] * ineq_coef, dim=-1)
                        < ineq_rhs
                    )
                    x_samples[violated_ind.nonzero(), ..., ineq_ind] = torch.rand(
                        sum(violated_ind), len(ineq_ind)
                    )

            if w_samples is None:
                init_w_samples = torch.rand(num_x_samples, num_init_w, dim_w)
            elif w_samples.size(0) >= num_init_w and weights is not None:
                idx = torch.multinomial(weights.repeat(num_x_samples, 1), num_init_w)
                init_w_samples = w_samples[idx]
            else:
                raise NotImplementedError
            kwargs["x_samples"] = x_samples
            kwargs["init_w_samples"] = init_w_samples
            kwargs["init_samples"] = torch.cat(
                (x_samples.unsqueeze(-2).repeat(1, num_init_w, 1), init_w_samples),
                dim=-1,
            )
            torch.random.set_rng_state(old_state)
        else:
            kwargs["x_samples"] = None
        if bm_alg_list[i] is None:
            q = q_base
        else:
            q = int(q_base / num_samples)
        output = exp_loop(
            function_name,
            seed=int(seed),
            dim_w=dim_w,
            filename=filename,
            iterations=iterations,
            num_samples=num_samples,
            num_fantasies=num_fantasies,
            num_restarts=num_restarts,
            raw_multiplier=raw_multiplier,
            q=q,
            apx=apx,
            random_sampling=random,
            tts_frequency=tts_frequency,
            benchmark_alg=bm_alg_list[i],
            w_samples=w_samples,
            **kwargs
        )
        output_dict[key][seed] = output
        print("%s, seed %s completed" % (key, seed))
print("Successfully completed!")
