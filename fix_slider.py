with open("pageCreator.py", "r") as f:
    text = f.read()

# the slider string
slider_str = '            ["SLIDER", 0, ["getVerticalMin", "getVeritcalMax", "getVerticalCurrentValue"]],\n'

# remove it from current pos
text = text.replace(slider_str, '')

# insert it after FINISH PAGE Sidebar
sidebar_end = '            ["FINISH PAGE", "Sidebar"],\n'
text = text.replace(sidebar_end, sidebar_end + slider_str)

with open("pageCreator.py", "w") as f:
    f.write(text)
print("Slider fixed")
