from internetarchive import search_items
print("Searching for 'identifier:structuraldesign00hovg'...")
s = search_items('identifier:structuraldesign00hovg')
print(f"Count: {s.num_found}")
for item in s:
    print(f"Found: {item['identifier']}")

print("-" * 20)
print("Searching for 'subject:naval architecture' limit 5...")
s2 = search_items('subject:"naval architecture"')
print(f"Count: {s2.num_found}")
i = 0
for item in s2:
    print(f"Found: {item['identifier']}")
    i += 1
    if i >= 5: break
