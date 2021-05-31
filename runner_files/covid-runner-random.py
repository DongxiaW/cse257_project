"""
This is the main file to be run on the cluster.
Modify this to fit the experiment you intend to run.
"""
from BoRisk import draw_constrained_sobol
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
iterations = 160

# seed_list = [int(sys.argv[1])]
seed_list = range(1, 31)

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
kwargs["dtype"] = torch.double

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
