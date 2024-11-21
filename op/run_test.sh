#!/bin/bash


cd ../app
export target_stock=BTC-USDT
python simulate_combat.py &

export target_stock=LUNC-USDT
python simulate_combat.py &

export target_stock=FLOKI-USDT
python simulate_combat.py &

export target_stock=OMI-USDT
python simulate_combat.py &

export target_stock=DOGE-USDT
python simulate_combat.py &

export target_stock=PEPE-USDT
python simulate_combat.py &




