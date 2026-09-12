from html.parser import HTMLParser
class P(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack=[]
    def handle_starttag(self, tag, attrs):
        if tag=='div':
            self.stack.append((tag, self.getpos()))
    def handle_endtag(self, tag):
        if tag=='div':
            if self.stack and self.stack[-1][0]=='div':
                self.stack.pop()
            else:
                print('unmatched end', self.getpos())
c=open(r'D:\SBC_Tool\templates\index.html', encoding='utf-8').read()
p=P()
p.feed(c)
print('remaining', len(p.stack))
for t,pos in p.stack[-10:]:
    print(t,pos)