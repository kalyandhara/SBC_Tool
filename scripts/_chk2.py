from html.parser import HTMLParser
class P(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack=[]
    def handle_starttag(self, tag, attrs):
        if tag=='div':
            self.stack.append('div')
    def handle_endtag(self, tag):
        if tag=='div':
            if self.stack: self.stack.pop()
            else: print('unmatched end')
# parse only tab-chakra part
c=open(r'D:\SBC_Tool\templates\index.html', encoding='utf-8').read()
i=c.find('id="tab-chakra"')
chunk=c[i:i+5000]
p=P()
p.feed(chunk)
print('remaining opens', len(p.stack))