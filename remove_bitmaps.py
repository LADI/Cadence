
from pathlib import Path
import os

resources = Path() / 'resources' / 'resources.qrc'

with open(resources, 'r') as f:
    contents = f.read()

new_lines = list[str]()

for line in contents.splitlines():
    stripline = line.strip()
    if not stripline.startswith('<file>'):
        new_lines.append(line)
        continue
    
    img = stripline.replace('<file>', '').replace('</file>', '')
    # print(img)
    if not img.endswith('/caleson.png'):
        print(img)
        for pyfile in os.listdir('src/'):
            if pyfile.endswith(('.py', '.ui')):
                # print(pyfile)
                with open('src/' + pyfile, 'r') as pyt:
                    pyconts = pyt.read()
                    if img.rpartition('/')[2].rpartition('.')[0] in pyconts:
                        new_lines.append(line)
                        # print('', img, pyfile)
                        break
        else:
            # print(img)
            os.remove('resources/' + img)
    else:
        new_lines.append(line)

# print(new_lines)
# print('\n'.join(new_lines))  
with open(resources, 'w') as f:
    f.write('\n'.join(new_lines))
