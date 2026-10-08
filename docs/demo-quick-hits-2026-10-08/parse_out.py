import sys, xml.etree.ElementTree as ET
root = ET.parse(sys.argv[1]).getroot()
for t in root.iter('test'):
    st = t.find('status')
    print('=== %s -> %s' % (t.get('name')[:70], st.get('status')))
    # failing keyword messages and console logs
    for kw in t.iter('kw'):
        s = kw.find('status')
        if s is not None and s.get('status') == 'FAIL':
            for m in kw.findall('msg'):
                print('   FAILKW', kw.get('name'), '|', (m.text or '')[:300].replace('\n',' '))
    for m in t.iter('msg'):
        txt = (m.text or '').strip()
        if any(k in txt for k in ('VERIFIED-PASS','CAUGHT-BUG','COULD-NOT-CHECK','holds before','read back','STOCK','GZ READ PAGE','GZ VERIFY','GZ SHOW','GarzAI')) and m.get('level') in ('INFO','WARN','FAIL',None):
            print('   ', m.get('level'), txt[:260].replace('\n',' | '))
    msg = st.text or ''
    if msg: print('   STATUS MSG:', msg[:400].replace('\n',' '))
