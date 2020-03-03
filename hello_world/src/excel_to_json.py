from json import loads, dumps
from pandas import read_excel
from selenium_handler import upload_file

df = read_excel('../docs/urls_example.xlsx', sheet_name='url')
print(df["perform_download"])
# build dictionary based on carriage returns
def build_dict(dict_lines):
    dict_return = {}
    # build dictionary based on carriage returns
    if isinstance(dict_lines, str) and dict_lines != "":

        for index, item in enumerate(dict_lines.splitlines()):
            dict_return[str(index + 1)] = loads("{" + item + "}")

    return dict_return

def time_estimator():

    pass
    # estimate the time it will take to load a page & perform clicks etc


# TODO: split up groups
# 1. get first record as setup step - assumed to be a login that therefore prevents multiple logins in parallel
# 2. get a cumulative time taken and cut-off at < 15 mins (or whatever aws time is set at)
# 3. for remaining groups inset record in # 1. and repeat
# 4. due to login assumption in # 1. processing has to be in sequence for these sub-groups


final_dict = {}

for index, row in df.iterrows():

    send_key_dict = build_dict(row['sendKeysToElement'])
    css_button = build_dict(row['css_button'])

    tmp_dict = {"step": row['step'],
                "send_keys_to_elements": send_key_dict,
                "perform_download": row["perform_download"],
                "prepend_to_name": row["prepend_to_name"],
                "final_click": row["final_click"],
                "css_button": css_button,
                "urls": row["urls"],
                "save_page_source": row["save_page_source"]
                }

    final_dict[str(index)] = tmp_dict



data = {}

data["selenium_commands"] = final_dict

text_file = open("../docs/commands.json", "w")
text_file.write(str(dumps(data)))
text_file.close()