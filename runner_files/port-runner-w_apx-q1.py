"""
This is the main file to be run on the cluster.
Modify this to fit the experiment you intend to run.
"""
from BoRisk import draw_constrained_sobol
from BoRisk.exp_loop import exp_loop
import torch
from BoRisk.test_functions import function_picker

# Modify this and make sure it does what you want!

function_name = "portfolio_surrogate"
num_samples = 40  # this is 40 for rhoKG / apx and 10 for benchmarks
num_fantasies = 10  # default 50
key_list = ["tts_w_apx_q=1"]
# this should be a list of bm algorithms corresponding to the keys. None if rhoKG
bm_alg_list = [None]
q_base = 1  # q for rhoKG. For others, it is q_base / num_samples
iterations = 80

import sys

seed_list = [int(sys.argv[1])]

output_file = "%s_%s" % (function_name, "var")
torch.manual_seed(0)  # to ensure the produced seed are same!
kwargs = dict()
if len(sys.argv) > 2:
    kwargs["device"] = sys.argv[2]
dim_w = 2
kwargs["noise_std"] = 0.1
kwargs[
    "negate"
] = True  # True if the function is written for maximization, e.g. portfolio
function = function_picker(function_name)
kwargs["fix_samples"] = True
w_samples = function.w_samples
weights = function.weights
kwargs["weights"] = weights
dim_x = function.dim - dim_w
num_restarts = 10 * function.dim
raw_multiplier = 50  # default 50

kwargs["random_w"] = True
kwargs["num_inner_restarts"] = 5 * dim_x
kwargs["CVaR"] = False
kwargs["expectation"] = False
kwargs["alpha"] = 0.8
kwargs["disc"] = False
kwargs["low_fantasies"] = 4
# kwargs["dtype"] = torch.double
num_x_samples = 8
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
        # init samples
        old_state = torch.random.get_rng_state()
        torch.manual_seed(seed)
        num_full_samples = num_x_samples * num_init_w
        init_samples = draw_constrained_sobol(
            bounds=torch.tensor([[0.0], [1.0]]).repeat(1, function.dim),
            n=num_full_samples,
            q=1,
            inequality_constraints=function.inequality_constraints,
        ).squeeze(-2)
        if w_samples is not None:
            init_samples[..., dim_x:] = w_samples[
                torch.randint(w_samples.shape[0], size=(num_full_samples,))
            ]
        torch.random.set_rng_state(old_state)
        output = exp_loop(
            function_name,
            seed=int(seed),
            dim_w=dim_w,
            filename=filename,
            iterations=iterations,
            num_samples=num_samples,
            num_fantasies=num_fantasies,
            num_restarts=num_restarts,
            init_samples=init_samples,
            raw_multiplier=raw_multiplier,
            q=q_base,
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
