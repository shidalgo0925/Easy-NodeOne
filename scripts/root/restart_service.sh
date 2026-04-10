#!/bin/bash
# Easy NodeOne (no tocar nodeone.service en projects/)
sudo systemctl start nodeone.service
sudo systemctl status nodeone.service --no-pager

