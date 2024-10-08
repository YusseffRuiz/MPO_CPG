import matplotlib.pyplot as plt
import numpy as np
import torch
from MatsuokaOscillator import MatsuokaOscillator, MatsuokaNetwork, MatsuokaNetworkWithNN
import os
import Adaptive_RL
from Adaptive_RL import SAC, DDPG, MPO, PPO, plot
import yaml
import argparse
import Experiments.experiments_utils as trials
# from myosuite.utils import gym
import gymnasium as gym

# Basic Matsuoka Oscillator Implementation
def matsuoka_main():
    # Parameters
    neural_net = False
    num_oscillators = 2
    neuron_number = 2
    tau_r = 2
    tau_a = 12
    w12 = 2.5
    u1 = 2.5
    beta = 2.5
    dt = 1
    steps = 1000
    weights = np.full(neuron_number, w12)
    time = np.linspace(0, steps * dt, steps)

    if neural_net is True:
        # Neural Network Implementation
        input_size = num_oscillators  # Example input size
        hidden_size = 10  # Hidden layer size
        output_size = 3  # tau_r, weights, and beta for each oscillator

        matsuoka_network = MatsuokaNetworkWithNN(num_oscillators=num_oscillators,
                                                 env=[1, neuron_number * num_oscillators], neuron_number=neuron_number,
                                                 tau_r=tau_r, tau_a=tau_a)
        # Create a sample sensory input sequence
        # sensory_input_seq = torch.rand(steps, num_oscillators, input_size, dtype=torch.float32, device="cuda")

        # Run the coupled system with NN control
        outputs = matsuoka_network.run(steps=steps)

        for i in range(num_oscillators):
            plt.plot(time, outputs[:, i, 0], label=f'Oscillator {i + 1} Neuron 1')
            plt.plot(time, outputs[:, i, 1], label=f'Oscillator {i + 1} Neuron 2')

        plt.xlabel('Time step')
        plt.ylabel('Output')
        plt.title('Outputs of Coupled Matsuoka Oscillators Controlled by NN')
        plt.legend()
        plt.grid(True)
        plt.show()

    else:
        # Run of the events
        if num_oscillators == 1:
            # Create Matsuoka Oscillator with N neurons
            oscillator = MatsuokaOscillator(neuron_number=neuron_number, tau_r=tau_r, tau_a=tau_a,
                                            beta=beta, dt=dt, action_space=neuron_number * num_oscillators,
                                            num_oscillators=num_oscillators)
            y_output = oscillator.run(steps=steps)

            for i in range(y_output.shape[1]):
                plt.plot(time, y_output[:, i], label=f'y{i + 1} (Neuron {i + 1})')
            plt.xlabel('Time')
            plt.ylabel('Output')
            plt.title('Matsuoka Oscillator Output')
            plt.legend()
            plt.grid(True)
            plt.show()
        else:
            # Coupled System
            coupled_system = MatsuokaNetwork(num_oscillators=num_oscillators, neuron_number=neuron_number, tau_r=tau_r,
                                             tau_a=tau_a, weights=weights, beta=beta, dt=dt,
                                             action_space=neuron_number * num_oscillators)
            y_output = coupled_system.run(steps=steps)

            # Coupled Oscillators
            for i in range(num_oscillators):
                for j in range(neuron_number):
                    plt.plot(time, y_output[i][:, j], label=f'Oscillator {i + 1} Neuron {j + 1}')

            plt.xlabel('Time step')
            plt.ylabel('Output')
            plt.title('Outputs of Coupled Matsuoka Oscillators')
            plt.legend()
            plt.grid(True)
            plt.show()


def train_agent(
        agent, environment, trainer=Adaptive_RL.Trainer(), parallel=1, sequential=1, seed=0,
        checkpoint="last", path=None, log_dir=None):
    """
    :param agent: Agent and algorithm to be trained.
    :param environment: Environment name
    :param trainer: Trainer to be used, at this moment, the default from tonic
    :param parallel: Parallel Processes
    :param sequential: Vector Environments.
    :param seed: random seed
    :param checkpoint: checkpoint to verify existence.
    :param path: Path where the experiment to check for checkpoints
    :param log_dir:: Path to add the logs of the experiment
    """
    torch.set_default_device('cuda' if torch.cuda.is_available() else "cpu")
    if torch.cuda.is_available():
        device = torch.cuda.get_device_name(torch.cuda.current_device())
        print(f"Runing with {device}")
    else:
        print("Running with CPU")
    path = log_dir
    args = dict(locals())
    checkpoint_path = None
    config = None
    # Process the checkpoint path same way as in tonic.play
    if path:
        checkpoint_path = Adaptive_RL.load_checkpoint(checkpoint, path)
        if checkpoint_path is not None:
            # Load the experiment configuration.
            arguments_path = os.path.join(path, 'config.yaml')
            with open(arguments_path, 'r') as config_file:
                config = yaml.load(config_file, Loader=yaml.Loader)
            config = argparse.Namespace(**config)

            agent = agent or config.agent
            environment = environment or config.test_environment
            environment = environment or config.environment
            trainer = trainer or config.trainer

    # Build the training environment.

    _environment = Adaptive_RL.Gym(environment)
    environment = Adaptive_RL.parallelize.distribute(
        lambda: _environment, parallel, sequential)
    environment.initialize() if parallel > 1 else 0

    # Build the testing environment.
    test_environment = Adaptive_RL.parallelize.distribute(
        lambda: _environment)

    # Build the agent.
    if not agent:
        raise ValueError('No agent specified.')

    agent.initialize(observation_space=environment.observation_space, action_space=environment.action_space,
                     seed=seed)

    # Load the weights of the agent form a checkpoint.
    if checkpoint_path:
        agent.load(checkpoint_path)

    # Initialize the logger to save data to the path
    Adaptive_RL.logger.initialize(path=log_dir, config=args)

    # Build the trainer.
    trainer.initialize(
        agent=agent, environment=environment,
        test_environment=test_environment)

    # Train.
    trainer.run()


if __name__ == "__main__":
    # register_new_env()
    training_mpo = "MPO"
    trianing_sac = "SAC"
    training_ppo = "PPO"
    training_algorithm = training_ppo

    # env_name = "Walker2d-v4"
    env_name = "Humanoid-v4"
    cpg_flag = False
    experiment_number = 0

    # Steps to train
    max_steps = int(1e7)
    epochs = int(max_steps / 500)
    save_steps = int(max_steps / 200)

    # Hyperparameters
    sequential = 8
    parallel = 4
    lr_actor = 3.56987e-05
    ent_coeff = 0.00238306
    clip_range = 0.3
    lr_critic = 3.56987e-05
    lr_dual = 1e-4
    gamma = 0.95
    neuron_number = 256
    layers_number = 3
    batch_size = 256
    replay_buffer_size = 10e5
    epsilon = 0.1

    env_name, save_folder, log_dir = trials.get_name_environment(env_name, cpg_flag=cpg_flag,
                                                                 algorithm=training_algorithm, create=True,
                                                                 experiment_number=experiment_number)

    if training_algorithm == "MPO":
        agent = MPO(lr_actor=lr_actor, lr_critic=lr_critic, lr_dual=lr_dual, hidden_size=neuron_number,
                    discount_factor=gamma, replay_buffer_size=replay_buffer_size, hidden_layers=layers_number)
    elif training_algorithm == "SAC":
        agent = SAC(lr_actor=lr_actor, lr_critic=lr_critic, hidden_size=neuron_number, discount_factor=gamma, hidden_layers=layers_number,)
    elif training_algorithm == "PPO":
        agent = PPO(lr_actor=lr_actor, lr_critic=lr_critic, hidden_size=neuron_number, hidden_layers=layers_number, discount_factor=gamma,
                    batch_size=batch_size, entropy_coeff=ent_coeff, clip_range=clip_range)
    else:
        agent = None

    if agent is not None:
        train_agent(agent=agent,
                    environment=env_name,
                    sequential=sequential, parallel=parallel,
                    trainer=Adaptive_RL.Trainer(steps=max_steps, epoch_steps=epochs, save_steps=save_steps),
                    log_dir=log_dir)

        env = gym.make(env_name, render_mode="human", max_episode_steps=1500)

        print("Starting Evaluation")
        trials.evaluate(agent, env, algorithm=training_algorithm, num_episodes=5)

        plot.plot(paths=save_folder, x_axis="train/seconds", x_label="Seconds", title=f"{env_name}_training")

        env.close()
    else:
        print("No agent specified, finishing program")
        exit()
