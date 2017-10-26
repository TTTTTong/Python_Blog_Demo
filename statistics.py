import os
import sys

lines = 0
blank = 0
for currentDir, fdir, file in os.walk('\\'.join(sys.argv[0].split('/')[:-1])):
    for f in file:
        if f.split('.')[-1] == 'py':
            path = os.path.join(currentDir, f)
            # print(path)
            with open(path, encoding='utf-8') as c:
                for line in c:
                    if line.strip():
                        lines += 1
                    else:
                        blank += 1
print('lines:', lines)
print('blank: ', blank)