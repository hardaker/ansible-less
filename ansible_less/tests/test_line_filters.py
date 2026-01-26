from ansible_less import AnsibleLess


def test_test():
    al = AnsibleLess()

    # host skippings are dropped
    results = al.filter_lines(["skipping: [myhost.localhost]"])
    assert results == []

    # ok lines are left
    results = al.filter_lines(["ok: [myhost.localhost]"])
    assert results == ["ok: [myhost.localhost]"]

    # date-only lines are dropped
    results = al.filter_lines(
        [
            "Tuesday 24 June 2025  22:45:56 +0000 (0:00:10.717)       0:01:48.510 ********** \n"
        ]
    )
    assert results == []

    # time sub-seconds are cleaned:
    results = al.filter_lines(
        [
            'xxx "mtime": 12345.678 and other stuff',
            'xxx "atime": 12345.678 and other things',
            'yyy "delta": "0:01:02.9876 and more delta',
        ]
    )
    assert results == [
        'xxx "mtime": 12345 and other stuff',
        'xxx "atime": 12345 and other things',
        'yyy "delta": "0:01:02 and more delta',
    ]


    # clean up tmpfilenames
    results = al.filter_lines(['+++ after: /home/user/.ansible/tmp/ansible-local-3524983q2d7vqwe/tmplxfgjne5/somefile.txt'])
    assert results == ['+++ after: /home/user/.ansible/tmp/.../somefile.txt']
