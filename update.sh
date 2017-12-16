#! /bin/bash

branch=$(cat "$HOME/.dhcpns.branch")
pushd "$HOME/dhcpns"
  git pull
  git fetch origin
  git checkout "$branch" && git reset --hard "origin/$branch" && git clean -f -d

  # Set permissions
  chmod -R 744 ./*
popd
