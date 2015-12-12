#! /bin/bash

ME=$(whoami)

branch=$(cat /home/$ME/.dhcpns.branch)
pushd /home/$ME/dhcpns
  git pull
  git fetch origin
  git checkout $branch && git reset --hard origin/$branch && git clean -f -d

  # Set permissions
  chmod -R 744 *
popd
