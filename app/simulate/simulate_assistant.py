class Account_info:
    def __init__(self):
        self.init_balance = 100
        self.balance = self.init_balance
        self.total_ratio = 1.0
        # self.risk_rate = 0.01
        # self.risk_rate = 0.003  # 由于时间周期减小，风险率也要减小,1H
        self.risk_rate = 0.0025  # 由于时间周期减小，风险率也要减小,4H
        self.total_cost = 0

        self.long_position = 0
        self.max_long_position = 2

        self.max_sell_times = 3
        self.sell_times = 0

        self.hold_price = 0
        self.open_price = 0

        self.hold_amount = 0
        self.max_hold_amount = 0

        self.return_rate_list = []

        self.make_money_times = 0
        self.lost_money_times = 0

        self.make_money_rate = 0
        self.lost_money_rate = 0

    def print_all_info(self):
        # 获取类的所有属性及其值
        attributes = vars(self)
        for attr, value in attributes.items():
            if attr == 'return_rate_list':
                continue
            print(f"{attr}: {value}")
        print(self.balance + self.hold_amount * self.hold_price)

        # return attributes
        return self.balance + self.hold_amount * self.hold_price

    def update_info(self, params):
        self.balance = params['balance']
        self.long_position = params['long_position']
        self.hold_price = params['hold_price']
        self.hold_amount = params['hold_amount']

        if "open_price" in params:
            self.open_price = params['open_price']

        if "init_balance" in params:
            self.init_balance = params['init_balance']

        if "max_hold_amount" in params:
            self.max_hold_amount = params['max_hold_amount']

        if "total_ratio" in params:
            self.total_ratio = params['total_ratio']

        if "sell_times" in params:
            self.sell_times = params['sell_times']

        if "total_cost" in params:
            self.total_cost = params['total_cost']


def sell(account_info, market_price, ratio=1.0, today_timestamp=None):
    amount = account_info.hold_amount
    if ratio < 1.0:
        amount = round(account_info.max_hold_amount * ratio, 5)
    if account_info.total_ratio < ratio:  # 不足部分全清
        print("清空")
        amount = account_info.hold_amount

    # 部分卖出
    position = account_info.long_position
    receive_money = amount * market_price
    receive_money = receive_money * (1 - DEAL_RATE)

    print(f"amount: {amount}, price: {market_price}")

    new_params = {
        "balance": account_info.balance + receive_money,
        "long_position": position,
        "hold_price": account_info.hold_price,
        "hold_amount": account_info.hold_amount - amount,
        "total_ratio": account_info.total_ratio - ratio,
        "sell_times": account_info.sell_times + 1
    }

    # 全部卖出
    account_ratio = account_info.total_ratio
    if ratio == 1.0 or account_ratio < ratio:
        new_params["hold_price"] = 0
        new_params["long_position"] = 0
        new_params["total_ratio"] = 0
        new_params["hold_amount"] = 0
        new_params["max_hold_amount"] = 0
        new_params["sell_times"] = 0
        new_params["total_cost"] = 0
        new_params["init_balance"] = account_info.balance + receive_money

    if ratio == 1.0 or account_ratio < ratio:
        # init_balance = account_info.init_balance
        # balance = account_info.balance + receive_money
        # delta = balance - init_balance
        # formatted_value = '{:.2%}'.format(delta / init_balance)
        # print(f"{round(balance, 3)}, {round(init_balance, 3)}")
        # print(f"!收益率: {formatted_value}")
        # account_info.return_rate_list.append([today_timestamp, round(delta / init_balance, 4)])

        total_cost = account_info.total_cost
        not_use_money = account_info.init_balance - total_cost
        total_increase = account_info.balance + receive_money - not_use_money
        delta = total_increase - total_cost
        formatted_value = '{:.2%}'.format(delta / total_cost)
        print(f"{round(total_increase, 3)}, {round(total_cost, 3)}")
        print(f"!收益率: {formatted_value}")
        if delta > 0:
            account_info.make_money_times += 1
            account_info.make_money_rate += delta / total_cost
        else:
            account_info.lost_money_times += 1
            account_info.lost_money_rate -= delta / total_cost

        account_info.return_rate_list.append([today_timestamp, round(delta / total_cost, 4)])

    account_info.update_info(new_params)
    print(f"balance: {round(account_info.balance, 3)}")
