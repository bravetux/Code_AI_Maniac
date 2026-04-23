def process(items):  # S3776 cognitive complexity
    out = []
    for i in items:
        if i > 0:
            if i % 2 == 0:
                if i < 100:
                    out.append(i * 2)
                else:
                    out.append(i)
            else:
                out.append(i + 1)
    return out


def _err():
    raise Exception("nope")  # S1192 + S5753
