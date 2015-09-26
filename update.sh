#! /bin/bash

branch=$(cat ~/.dhcpns.branch)
git pull
git fetch origin
git checkout $branch && git reset --hard origin/$branch && git clean -f -d

# Set permissions
chmod -R 744 *
