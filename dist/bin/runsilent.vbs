Dim sh : Set sh = CreateObject("WScript.Shell")
sh.CurrentDirectory = "C:\root\bin\zapretgui\dist\bin\"
cmd = """" & "C:\root\bin\zapretgui\dist\bin\winws.exe" & """"
cmd = cmd & " --wf-l3=ipv4,ipv6 --wf-tcp=80,443 --wf-udp=443,50000-50099"
cmd = cmd & " --filter-tcp=80 --dpi-desync=fake,fakedsplit --dpi-desync-autottl=2 --dpi-desync-fooling=md5sig --new"
cmd = cmd & " --filter-tcp=443 --hostlist=""youtube.txt"" --dpi-desync=fake,multidisorder --dpi-desync-split-pos=1,midsld --dpi-desync-repeats=11 --dpi-desync-fooling=md5sig  --dpi-desync-fake-tls-mod=rnd,dupsid,sni=www.google.com --new"
cmd = cmd & " --filter-tcp=443 --hostlist=""other.txt"" --hostlist=""discord.txt"" --hostlist=""faceinsta.txt"" --dpi-desync=fake,multidisorder --dpi-desync-split-pos=midsld --dpi-desync-repeats=6 --dpi-desync-fooling=badseq,md5sig --new"
cmd = cmd & " --filter-udp=443 --hostlist=""youtube.txt"" --dpi-desync=fake --dpi-desync-repeats=11 --dpi-desync-fake-quic=""quic_initial_www_google_com.bin"" --new"
cmd = cmd & " --filter-udp=443 --dpi-desync=fake --dpi-desync-repeats=11 --new"
cmd = cmd & " --filter-udp=50000-50099 --filter-l7=discord,stun --dpi-desync=fake"
sh.Run cmd, 0, False          ' 0 = hidden, False = не ждать завершения
