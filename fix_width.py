with open("QtWrapper/windowManager.py", "r") as f:
    text = f.read()

width_code = """
            elif setting[DisplayBase.QTTYPE] == "FIXED_WIDTH":
                row.setWidth(int(setting[DisplayBase.SHOWNAME]))

"""

text = text.replace('            elif setting[DisplayBase.QTTYPE] == "CREATE PAGE":', width_code + '            elif setting[DisplayBase.QTTYPE] == "CREATE PAGE":')

with open("QtWrapper/windowManager.py", "w") as f:
    f.write(text)
print("Added FIXED_WIDTH")
