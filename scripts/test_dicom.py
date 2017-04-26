import dicom.sequence

xnat = dicom.read_file(
    '/Users/tclose/Downloads/xnat/'
    '1.3.12.2.1107.5.2.19.45193.30000016011322291287700000005-1-1-14j031j.dcm')

daris = dicom.read_file('/Users/tclose/Downloads/daris/0002.dcm')

EXCLUDED_TAGS = []


def compare(xnat_elem, daris_elem, ns=None):
    if ns is None:
        ns = []
    name = '.'.join(ns)
    if isinstance(daris_elem, dicom.dataset.Dataset):
        for d in daris_elem:
            if d.tag not in EXCLUDED_TAGS:
                try:
                    x = xnat_elem[d.tag]
                except KeyError:
                    print("missing {}".format(daris_elem))
                compare(x, d, ns=ns + [d.name])
    elif isinstance(daris_elem.value, dicom.sequence.Sequence):
        if len(xnat_elem.value) != len(daris_elem.value):
            print("Mismatching length of '{}' sequence (xnat:{} vs daris:{})"
                  .format(name, len(xnat_elem.value), len(daris_elem.value)))
        for x, d in zip(xnat_elem.value, daris_elem.value):
            compare(x, d, ns=ns)
    else:
        if xnat_elem.value != daris_elem.value:
            include_diff = True
            try:
                if max(len(xnat_elem.value), len(daris_elem.value)) > 100:
                    include_diff = False
            except TypeError:
                pass
            if include_diff:
                diff = ('(xnat:{} vs daris:{})'
                              .format(xnat_elem.value, daris_elem.value))
            else:
                diff = ''
            print("mismatching value for '{}'{}".format(name, diff))

compare(xnat, daris)
