import torch
from torch import nn
from torch._C import device
from torch import optim
import random
import numpy as np
from collections import deque
import skimage
from wandb import wandb
from graphs import graph
import gym
import gym_ple
import DQN
import CNN
##HYPERPARAMETERS
learning_rate = 0.00025 ## 0.00025 ~ 100avg reward after 10m iterations 0.00001 lr to achieve around 280 avr reward
EPISODES = 5000
INPUTSIZE = (84,84)
START_TRAINING_AT_STEP = 5000
TRAINING_FREQUENCY = 4
TARGET_NET_UPDATE_FREQUENCY = 10000
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Using {device} device")
torch.autograd.set_detect_anomaly(True)
   
def getFrame(x):
    #x = x[35:210,0:160]## For breakout, pong
    x = x[0:405,0:288] #flappybird
    #x = x[75:170,10:160]#For robotank :D
    state = skimage.color.rgb2gray(x)
    state = skimage.transform.resize(state, INPUTSIZE)
    state = skimage.exposure.rescale_intensity(state,out_range=(0,255))
    state = state.astype('uint8')
    return state

def makeState(state):
    return np.stack((state[0],state[1],state[2],state[3]), axis=0)

def clip_reward(reward):
    if reward > 0:
        return 1
    elif reward < 0:
        return -1
    else:
        return 0

def train(game):
    #import time
    env = gym.make(game)
    y = CNN.NeuralNetwork(env.action_space.n, None).to(device)
    target_y = CNN.NeuralNetwork(env.action_space.n, None).to(device)
    loss_fn = nn.HuberLoss()
    optimizer = optim.Adam(y.parameters(), lr = learning_rate)
    agent = DQN.DQN()
    state = deque(maxlen = 4)
    print(y)
    answer = input("Use a pre-trained model y/n? ")
    if answer == "y":
        agent.loadModel(y,'pixel_atari_weights.pth')
        agent.loadModel(target_y,'pixel_atari_weights.pth')
    frames_seen = 0
    rewards = []
    avgrewards = []
    loss = []
    wandb.init(project="BREAKOUT_DQN", entity="neuroori") 
    for episode in range(1,EPISODES+500000000000):
        obs = env.reset()
        cumureward = 0
        lives = 0 ## 5 for breakout, 3 for spaceinvaders, 0 for pong, 3 for robotank :D
        state.append(getFrame(obs))
        state.append(getFrame(obs))
        state.append(getFrame(obs))
        state.append(getFrame(obs))
        while True:
            action = agent.getPrediction(makeState(state)/255,y)
            ##Repeat same action four times for flappybird/doom otherwise set it to one.
            for repeat in range(4):
                obs, reward, done, info = env.step(action)
                if done or reward == 1:
                    break
            ##uncomment for atari
            #if info["ale.lives"] < lives:
            #    done = True
            #    lives -= 1
            env.render()
            cache = state.copy()
            state.append(getFrame(obs))
            agent.update_replay_memory((makeState(cache), action, clip_reward(reward), makeState(state), done))
            ##Train the agent
            if len(agent.replay_memory) >= START_TRAINING_AT_STEP and frames_seen % TRAINING_FREQUENCY == 0:
                loss.append(agent.train(y, target_y, loss_fn, optimizer))
            ##Update target network  
            if len(agent.replay_memory) >= START_TRAINING_AT_STEP and frames_seen % TARGET_NET_UPDATE_FREQUENCY == 0:
                target_y.load_state_dict(y.state_dict())
                print("Target net updated.")
            frames_seen+=1
            cumureward += reward
            if frames_seen % 10000 == 0:
                agent.saveModel(y,'pixel_atari_weights.pth')
            if done and lives == 0:
                break
        rewards.append(cumureward)
        avgrewards.append(np.sum(np.array(rewards))/episode)
        print("Score:", cumureward, " Episode:", episode, " frames_seen:", frames_seen , " Epsilon:", agent.EPSILON)
        wandb.log({"Reward per episode":cumureward, "Avg reward":(np.sum(np.array(rewards))/episode), "Loss":loss})
        if len(loss)>0:
            loss = []

def test(game):
    import time
    env = gym.make(game)
    y = CNN.NeuralNetwork(env.action_space.n, None).to(device)
    agent = DQN.DQN()
    agent.loadModel(y,'pixel_atari_weights.pth')
    state = deque(maxlen = 4)
    print(y)
    lives = 0
    score = 0
    obs = env.reset()
    state.append(getFrame(obs))
    state.append(getFrame(obs))
    state.append(getFrame(obs))
    state.append(getFrame(obs))
    rewards = []
    avgrewards = []
    cumureward = 0
    games = 1
    while True:
        action = agent.getPrediction(makeState(state)/255,y)
        for i in range(4):
            obs, reward, done, info = env.step(action)
        state.append(getFrame(obs))
        score += reward
        cumureward += reward
        env.render()
        time.sleep(1/30)
        #if info["ale.lives"] < lives:
        #    done = True
        #    lives -= 1
        if done and lives == 0:
            lives = 0
            obs = env.reset()
            #obs, reward, done, info = env.step(1)
            state.append(getFrame(obs))
            state.append(getFrame(obs))
            state.append(getFrame(obs))
            state.append(getFrame(obs))
            print("Score: ", score, " Game: " , games)
            score = 0
            rewards.append(cumureward)
            avgrewards.append(np.sum(np.array(rewards))/games)
            cumureward = 0
            games += 1
        if games == 100:
            break
    graph(rewards, avgrewards, [], "fetajuusto/DQN-FLAPPY-PIXEL")

if __name__ == "__main__":
    #game = 'BreakoutDeterministic-v4'
    #game = "SpaceInvadersDeterministic-v4"
    #game = "PongDeterministic-v4"
    #game = "RobotankDeterministic-v4"
    game = 'FlappyBird-v0'
    train(game)
    #test(game)