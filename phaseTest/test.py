# a = [(1, 2), (4, 1), (9, 10), (13, -3)]
# a.sort(key=lambda x: x[1])
# print(a)

list1 = [1, 2, 4, 7, 5, 3]
list2 = [4, 5, 3, 2, 9, 1]
data = zip(list1, list2)
# print('---', list(data))
data = sorted(data)
print(data)
list1, list2 = map(lambda t: list(t), zip(*data))
print(list1)
print(list2)