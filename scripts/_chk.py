c=open(r'D:\SBC_Tool\templates\index.html', encoding='utf-8').read()
start=c.find('id="tab-chakra"')
s=c[start:start+4000]
print('div open', s.count('<div'), 'close', s.count('</div>'))
print('section open', s.count('<section'), 'close', s.count('</section>'))
