from guizero import App, Text, PushButton, Combo, CheckBox, ButtonGroup

def btn_cmd():
    test_text.value = "Clicked"

app = App( title="Yo", width=200, height = 160, layout="grid" )
test_text = Text( app, text="Text", grid=[0, 0], align="left" )
test_btn = PushButton( app, command=btn_cmd, text="Click", grid=[1,1], align="left" )
test_combo = Combo( app, options=["Option 1", "Option 2"], grid=[0, 1], align="left" )
test_check = CheckBox( app, text="Check", grid=[0, 2], align="left" )
test_radio = ButtonGroup( app, options=[ ["A", "A"], ["B", "B"] ], selected="A", horizontal=False, grid=[1, 0], align="left" )
app.display()
