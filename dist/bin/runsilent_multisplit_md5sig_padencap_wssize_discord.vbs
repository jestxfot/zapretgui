Dim sh : Set sh = CreateObject("WScript.Shell")
sh.CurrentDirectory = "C:\root\bin\zapretgui\dist\bin\"
cmd = """" & "C:\root\bin\zapretgui\dist\bin\winws.exe" & """"
cmd = cmd & " --wf-tcp=443 --wf-udp=443,50000-65535"
cmd = cmd & " --filter-udp=443 --hostlist=""discord.txt"" --dpi-desync=fake --dpi-desync-udplen-increment=10 --dpi-desync-repeats=6 --dpi-desync-udplen-pattern=0xDEADBEEF --dpi-desync-fake-quic=""quic_initial_www_google_com.bin"" --new"
cmd = cmd & " --filter-udp=50000-59000 --dpi-desync=fake --dpi-desync-any-protocol --dpi-desync-cutoff=d3 --dpi-desync-repeats=6 --dpi-desync-fake-quic=""quic_initial_www_google_com.bin"" --new"
cmd = cmd & " --filter-udp=443 --hostlist=""youtubeQ.txt"" --dpi-desync=fake --dpi-desync-repeats=11 --dpi-desync-fake-quic=""quic_initial_www_google_com.bin"" --new"
cmd = cmd & " --filter-tcp=443 --dpi-desync=fake,multisplit --dpi-desync-ttl=1 --dpi-desync-split-pos=1,midsld --dpi-desync-fake-tls-mod=rnd,rndsni,padencap --wssize 1:6"
sh.Run cmd, 0, False ' 0 = hidden, False = не ждать завершения
