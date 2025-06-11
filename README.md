Some notes:

* Modify the mount points as needed. Look into hard-linking when working out your media mount points. It lets you essentially sym link files from your downloader to your media storage. Keeps you from doubling up on storage. There is some config on the *arr apps you need to do to make that work.
* All the *arr apps and download clients are behind the VPN. You can still access them through the traefik addresses. No ports need to be exposed on those containers.
* I use URLs pointing to tailscale IPs for my plex.domain.com and overseer.domain.com. But you could run these through traefik if you already have that working.
* First run will probably be an issue. After it is up, you will need to get into the various tools and get an API key to go into .env. From there you can restart everything.
* This is setup to use ProtonVPN
* You will setup your indexers through Prowlarr instead of in each *arr app.
* You still setup download clients in radarr and sonarr directly.
* In Overseerr, you will use things like "http://vpn:7878" to access Radarr or "http://vpn:8989" for Sonarr.
* For port forwarding across the VPN, you need to read the docs on http://ghcr.io/t-anc/gsp-qbittorent-gluetun-sync-port-mod:main. You will have to take some extra steps here. This mod allows auto-updating the port forwarding you need for the VPN.
