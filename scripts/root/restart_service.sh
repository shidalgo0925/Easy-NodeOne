#!/bin/bash
# Easy NodeOne (no tocar membresia-relatic.service en projects/)
sudo systemctl start nodeone.service
sudo systemctl status nodeone.service --no-pager

