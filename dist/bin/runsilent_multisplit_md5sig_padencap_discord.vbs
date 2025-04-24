Dim sh : Set sh = CreateObject("WScript.Shell")
sh.CurrentDirectory = "C:\root\bin\zapretgui\dist\bin\"
cmd = """" & "C:\root\bin\zapretgui\dist\bin\winws.exe" & """"
cmd = cmd & " --wf-tcp=443 --wf-udp=443,50000-65535"
cmd = cmd & " --filter-tcp=443 --hostlist=""other.txt"" --hostlist=""faceinsta.txt"" --dpi-desync=fake,multisplit --dpi-desync-split-seqovl=1 --dpi-desync-split-pos=1 --dpi-desync-fake-tls=""tls_clienthello_vk_com.bin"" --dpi-desync-ttl=5 --new"
cmd = cmd & " --filter-udp=443 --hostlist=""discord.txt"" --dpi-desync=fake --dpi-desync-udplen-increment=10 --dpi-desync-repeats=6 --dpi-desync-udplen-pattern=0xDEADBEEF --dpi-desync-fake-quic=""quic_initial_www_google_com.bin"" --new"
cmd = cmd & " --filter-udp=50000-59000 --dpi-desync=fake --dpi-desync-any-protocol --dpi-desync-cutoff=d3 --dpi-desync-repeats=6 --dpi-desync-fake-quic=""quic_initial_www_google_com.bin"" --new"
cmd = cmd & " --filter-tcp=443 --hostlist=""youtubeGV.txt"" --dpi-desync=split --dpi-desync-split-pos=1 --dpi-desync-fooling=badseq --dpi-desync-repeats=10 --dpi-desync-cutoff=d2 --dpi-desync-ttl=4 --new"
cmd = cmd & " --filter-tcp=443 --hostlist=""youtube.txt"" --dpi-desync=fake,split2 --dpi-desync-split-seqovl=625 --dpi-desync-split-tls=sniext --dpi-desync-fake-tls=""tls_clienthello_vk_com.bin"" --dpi-desync-ttl=2 --new"
cmd = cmd & " --filter-udp=443 --hostlist=""youtubeQ.txt"" --dpi-desync=fake --dpi-desync-repeats=11 --dpi-desync-fake-quic=""quic_initial_www_google_com.bin"" --new"
cmd = cmd & " --filter-tcp=443 --hostlist=""discord.txt"" --ipset=""ipset-cloudflare.txt"" --dpi-desync=fake,multisplit --dpi-desync-ttl=1 --dpi-desync-split-pos=1,midsld --dpi-desync-fake-tls-mod=rnd,rndsni,padencap"
sh.Run cmd, 0, False ' 0 = hidden, False = не ждать завершения
