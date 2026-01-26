from ansible_less import AnsibleLess


def test_test():
    al = AnsibleLess()

    # check lines are grouped by host names and status
    results = al.group_by_hosts(
        [
            "Wednesday 17 December 2025  15:41:07 +0000 (0:00:16.929)       0:00:16.990 ",
            "**** \n",
            "--- before: /home/hardaker/tests/file.txt (content)\n",
            "+++ after: /home/hardaker/tests/file.txt " "(content)\n",
            "@@ -0,0 +1 @@\n",
            "+12/17/25 15:41:07 by hardaker\n",
            "\n",
            "\n",
            "changed: [host4.localhost]\n",
            "--- before: /home/hardaker/tests/file.txt (content)\n",
            "+++ after: /home/hardaker/tests/file.txt " "(content)\n",
            "@@ -0,0 +1 @@\n",
            "+12/17/25 15:41:07 by hardaker\n",
            "\n",
            "\n",
            "changed: [host2.localhost]\n",
            "ok: [host3.localhost]" "\n",
            "\n",
            "--- before: /home/hardaker/tests/file.txt (content)\n",
            "+++ after: /home/hardaker/tests/file.txt " "(content)\n",
            "@@ -0,0 +1 @@\n",
            "+12/17/25 15:41:07 by hardaker\n",
            "\n",
            "\n",
            "changed: [host1.localhost]\n",
        ]
    )

    ok_statuses = {"host3.localhost": "ok"}
    for hostnum in range(1, 5):
        hostname = f"host{hostnum}.localhost"
        assert hostname in results
        assert "lines" in results[hostname]
        assert "status" in results[hostname]
        assert results[hostname]["status"] == ok_statuses.get(hostname, "changed")





def test_multiple_statuses():
    al = AnsibleLess()
    results = al.group_by_hosts(
        [
            'ok: [host1.localhost] => (item=templateout1.conf)\n',
            'ok: [host2.localhost] => (item=templateout1.conf)\n',
            'ok: [host1.localhost] => (item=templateout2.conf)\n',
            'ok: [host2.localhost] => (item=templateout2.conf)\n',
            'changed: [host1.localhost] => (item=templateout3.conf)\n',
            'changed: [host2.localhost] => (item=templateout3.conf)\n',
            'ok: [host1.localhost] => (item=templateout4.conf)\n',
            'ok: [host2.localhost] => (item=templateout4.conf)\n',
        ]
    )

    for hostnum in range(1, 3):
        hostname = f"host{hostnum}.localhost"
        assert hostname in results
        assert "lines" in results[hostname]
        assert "status" in results[hostname]
        assert results[hostname]["status"] == "changed"
        assert results[hostname]['lines'] == [
            f'=> (item=templateout1.conf)\n',
            f'=> (item=templateout2.conf)\n',
            f'=> (item=templateout3.conf)\n',
            f'=> (item=templateout4.conf)\n',
        ]

def test_multiple_statuses():
    al = AnsibleLess()
    results = al.group_by_hosts(
        [
            'ok: [host1.localhost] => (item=templateout1.conf)\n',
            'fatal: [host2.localhost] => (item=templateout1.conf)\n',
            'ok: [host1.localhost] => (item=templateout2.conf)\n',
            'ok: [host2.localhost] => (item=templateout2.conf)\n',
            'ok: [host1.localhost] => (item=templateout3.conf)\n',
            'changed: [host2.localhost] => (item=templateout3.conf)\n',
            'ok: [host1.localhost] => (item=templateout4.conf)\n',
            'ok: [host2.localhost] => (item=templateout4.conf)\n',
        ]
    )

    assert results['host1.localhost']["status"] == "ok"
    assert results['host2.localhost']["status"] == "fatal"
    for hostnum in range(1, 3):
        hostname = f"host{hostnum}.localhost"
        assert hostname in results
        assert "lines" in results[hostname]
        assert "status" in results[hostname]
        assert results[hostname]['lines'] == [
            f'=> (item=templateout1.conf)\n',
            f'=> (item=templateout2.conf)\n',
            f'=> (item=templateout3.conf)\n',
            f'=> (item=templateout4.conf)\n',
        ]
        
