#! /bin/sh

download() {
  if command -v -- "wget" > /dev/null 2>&1; then
    wget "$1"
  elif command -v -- "curl" > /dev/null 2>&1; then
    curl -LO "$1"
  else
    printf "%s\n" "Unable to download required file"
    exit 1
  fi
}

(download "https://github.com/lavalink-devs/Lavalink/releases/download/4.0.4/Lavalink.jar" &&
 mv Lavalink.jar dectalk) &
(download "https://github.com/dectalk/dectalk/releases/download/2023-10-30/ubuntu-latest.tar.gz" &&
 mkdir -p dectalk/dectalk &&
 tar -C dectalk/dectalk -xf ubuntu-latest.tar.gz ./dic ./lib ./DECtalk.conf ./say &&
 rm ubuntu-latest.tar.gz) &
wait
