content = open('high_end_ws_lounge/database.py', 'r', encoding='utf-8').read()

# Fix the corrupted parts
content = content.replace("from wtforms import BooleanField, DateField, DateTimeField, DecimalField, HiddenField, IntegerField, PasswordField, \\\n    SelectField, StringField, SubmitField, TextAreaField, TimeField, lField",
                         "from wtforms import BooleanField, DateField, DateTimeField, DecimalField, HiddenField, IntegerField, PasswordField, \\\n    SelectField, StringField, SubmitField, TextAreaField, TimeField")

content = content.replace("def __repr__(self):\n        return f\"<Room {self.name}>\"",
                         "    def __repr__(self):\n        return f\"<Room {self.name}>\"")

content = content.replace("</old_str>\n</edit_file>\n    end_time = db.Column(db.DateTime, nullable=True)",
                         "    end_time = db.Column(db.DateTime, nullable=True)")

with open('high_end_ws_lounge/database.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('File fixed')
