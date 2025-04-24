Dim sh : Set sh = CreateObject("WScript.Shell")
sh.CurrentDirectory = "C:\root\bin\zapretgui\dist\bin\"
cmd = """" & "C:\root\bin\zapretgui\dist\bin\winws.exe" & """"
cmd = cmd & " --wf-tcp=80,443 --wf-udp=443,50000-50100"
cmd = cmd & " --filter-udp=443 --hostlist=""discord.txt"" --ipset=""ipset-cloudflare.txt"" --dpi-desync=fake --dpi-desync-repeats=6 --dpi-desync-fake-quic=""quic_initial_www_google_com.bin"" --new"
cmd = cmd & " --filter-udp=50000-50100 --ipset=""ipset-discord.txt"" --dpi-desync=fake --dpi-desync-any-protocol --dpi-desync-cutoff=d3 --dpi-desync-repeats=6 --new"
cmd = cmd & " --filter-tcp=80 --hostlist=""discord.txt"" --ipset=""ipset-cloudflare.txt"" --dpi-desync=fake,split2 --dpi-desync-autottl=2 --dpi-desync-fooling=md5sig --new"
cmd = cmd & " --filter-tcp=443 --hostlist=""discord.txt"" --hostlist=""youtube.txt"" --hostlist=""other.txt"" --ipset=""ipset-cloudflare.txt"" --dpi-desync=fake --dpi-desync-fooling=md5sig --dpi-desync-fake-tls-mod=rnd,rndsni,padencap --new"
sh.Run cmd, 0, False ' 0 = hidden, False = не ждать завершения
