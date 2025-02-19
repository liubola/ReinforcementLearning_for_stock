import random
import gym
import numpy as np
from gym import spaces
import yaml

with open('config.yaml') as f:
    args = yaml.safe_load(f)

MAX_ACCOUNT_BALANCE = 2147483647
MAX_NUM_SHARES = 2147483647
MAX_SHARE_PRICE = 5000
MAX_VOLUME = 1000e8
MAX_AMOUNT = 3e10
MAX_OPEN_POSITIONS = 5
MAX_STEPS = 20000
MAX_DAY_CHANGE = 1

INITIAL_ACCOUNT_BALANCE = args['env_args']['initial_account_balance']

def feature_engineer(df, current_step):
    feas = [
        df.loc[current_step, 'open'] / MAX_SHARE_PRICE,
        df.loc[current_step, 'high'] / MAX_SHARE_PRICE,
        df.loc[current_step, 'low'] / MAX_SHARE_PRICE,
        df.loc[current_step, 'close'] / MAX_SHARE_PRICE,
        df.loc[current_step, 'volume'] / MAX_VOLUME,
    ]
    return feas

class StockTradingEnv(gym.Env):
    """A stock trading environment for OpenAI gym"""
    metadata = {'render.modes': ['human']}

    def __init__(self, df):
        super(StockTradingEnv, self).__init__()

        self.df = df
        self.reward_range = (0, MAX_ACCOUNT_BALANCE)

        # Actions of the format Buy x%, Sell x%, Hold, etc.
        self.action_space = spaces.Box(
            low=np.array([0, 0]), high=np.array([3, 1]), dtype=np.float16)

        self.observation_space = spaces.Box(
            low=0, high=1, shape=(11,), dtype=np.float16)

    def _next_observation(self):

        feas = feature_engineer(self.df, self.current_step)
        obs = np.array(feas + [
            self.balance / MAX_ACCOUNT_BALANCE,
            self.max_net_worth / MAX_ACCOUNT_BALANCE,
            self.shares_held / MAX_NUM_SHARES,
            self.cost_basis / MAX_SHARE_PRICE,
            self.total_shares_sold / MAX_NUM_SHARES,
            self.total_sales_value / (MAX_NUM_SHARES * MAX_SHARE_PRICE),
        ])
        return obs

    def _take_action(self, action):
        # Set the current price to a random price within the time step
        current_price = random.uniform(
            self.df.loc[self.current_step, "open"], self.df.loc[self.current_step, "close"])

        action_type = action[0]
        amount = action[1]

        if action_type < 1:
            # Buy amount % of balance in shares
            additional_cost = self.balance * amount
            if additional_cost <= 20000:
                shares_bought = (additional_cost-5)/current_price # 此时手续费为5元
            else:
                # 买入价格为 current_price * (1+交易佣金费率)
                shares_bought = additional_cost / (current_price * (1 + args['env_args']['commission']))
            prev_cost = self.cost_basis * self.shares_held
            self.balance -= additional_cost
            self.cost_basis = (
                prev_cost + additional_cost) / (self.shares_held + shares_bought)
            self.shares_held += shares_bought

        elif action_type < 2:
            # Sell amount % of shares held
            shares_sold = int(self.shares_held * amount)
            # 卖出获得的现金为: 卖出份额*当前股票价格*(1-交易佣金费率)
            current_get_balance = shares_sold * current_price * (1 - args['env_args']['commission'])
            self.balance += current_get_balance
            self.shares_held -= shares_sold
            self.total_shares_sold += shares_sold
            self.total_sales_value += current_get_balance

        # 当前持有总资产:现金+股票
        self.net_worth = self.balance + self.shares_held * current_price * (1 - args['env_args']['commission'])

        if self.net_worth > self.max_net_worth:
            self.max_net_worth = self.net_worth

        if self.shares_held == 0:
            self.cost_basis = 0

    def step(self, action):
        # Execute one time step within the environment
        self._take_action(action)
        done = False

        self.current_step += 1

        if self.current_step > len(self.df.loc[:, 'open'].values) - 1:
            # self.current_step = 0  # loop training
            self.current_step = random.randint(6, len(self.df) - 1)
            # done = True


        # reward 1:
        # reward = self.net_worth - INITIAL_ACCOUNT_BALANCE
        # reward = 1 if reward > 0 else -100
        # 需要修改 self.reward_range = (0, MAX_ACCOUNT_BALANCE)


        # reward 2:
        delay_modifier = (self.current_step / MAX_STEPS)
        reward = self.balance * delay_modifier

        if self.net_worth <= 0:
            done = True

        obs = self._next_observation()

        return obs, reward, done, {}

    def reset(self, new_df=None, test=False):
        # Reset the state of the environment to an initial state
        self.balance = INITIAL_ACCOUNT_BALANCE
        self.net_worth = INITIAL_ACCOUNT_BALANCE
        self.max_net_worth = INITIAL_ACCOUNT_BALANCE
        self.shares_held = 0
        self.cost_basis = 0
        self.total_shares_sold = 0
        self.total_sales_value = 0

        # pass test dataset to environment
        if new_df:
            self.df = new_df

        # Set the current step to a random point within the data frame
        self.current_step = 0

        return self._next_observation()

    def render(self, mode='human', close=False):
        # Render the environment to the screen
        profit = self.net_worth - INITIAL_ACCOUNT_BALANCE
        date = self.df.loc[self.current_step - 1, "date"]
        open = self.df.loc[self.current_step - 1, "open"]
        close = self.df.loc[self.current_step - 1, "close"]
        high = self.df.loc[self.current_step - 1, "high"]
        low = self.df.loc[self.current_step - 1, "low"]

        print('-'*30)
        print(f'date: {date}')
        print(f'Step: {self.current_step}')
        print(f'Balance: {self.balance}')
        print(f'Shares held: {self.shares_held} (Total sold: {self.total_shares_sold})')
        print(f'Avg cost for held shares: {self.cost_basis} (Total sales value: {self.total_sales_value})')
        print(f'Net worth: {self.net_worth} (Max net worth: {self.max_net_worth})')
        print(f'Profit: {profit}')

        print(f'open:{open} close:{close}, high:{high}, low: {low}')

        return date, profit, open, close, high, low
