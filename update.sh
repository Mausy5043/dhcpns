#! /bin/bash

BRANCH=$(cat "$HOME/.dhcpns.branch")
pushd "$HOME/dhcpns"
  git fetch origin
  # Check which files have changed
  DIFFLIST=$(git --no-pager diff --name-only "$BRANCH..origin/$BRANCH")
  git pull
  git fetch origin
  git checkout "$BRANCH"
  git reset --hard "origin/$BRANCH" && git clean -f -d
popd
