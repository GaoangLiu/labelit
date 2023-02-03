#!/usr/bin/env python3
import os
import sqlite3
from typing import List, Tuple

import codefast as cf
import pandas as pd
import streamlit as st

dbfile = '/tmp/labelit.db'
db = sqlite3.connect(dbfile)
db.execute(
    'create table if not exists tags (md5 text primary key, content text, target text)'
)


def insert(md5: str, content: str, target: str):
    db.execute(
        'insert into tags values (?, ?, ?) on conflict(md5) do update set target=?',
        (md5, content, target, target))
    db.commit()


# Set the title of the application
st.set_page_config(page_title="Easy labelling",
                   page_icon="🧊",
                   layout="wide",
                   initial_sidebar_state="expanded",
                   menu_items={
                       'Get Help':
                       'https://www.extremelycoolapp.com/help',
                       'Report a bug':
                       "https://www.extremelycoolapp.com/bug",
                       'About':
                       "# This is a header. This is an *extremely* cool app!"
                   })

if 'num' not in st.session_state:
    st.session_state.num = 0
if 'data' not in st.session_state:
    st.session_state.data = []


def cf_force(file_name: str):
    # download file from host.ddot.cc each time
    tmp_file = '/tmp/' + file_name
    if not cf.io.exists(tmp_file):
        cf.net.download('https://host.ddot.cc/{}'.format(file_name), tmp_file)
    return tmp_file


class NewSample(object):

    def __init__(self, item_id: int, paragraph: List[str], choices: Tuple[str,
                                                                          str]):
        self.item_id = item_id
        self.content = '\n'.join(paragraph)
        self.choices = (str(c) for c in choices)
        st.text_area('对话内容', self.content, height=130)
        st.write('选择对应的的标签值（可多选）：')
        _tag_values = []
        for c in self.choices:
            if st.checkbox(c):
                _tag_values.append(c)
        self.target = ','.join(_tag_values)

    def persist(self):
        content = self.content.replace('\n', '/')
        md5 = cf.utils.md5sum(content)
        insert(md5, content, self.target)


def format_para(para: str) -> str:
    order, content = para.split('|', 1)
    content = content.replace('|', ': ')
    return '-'.join([order, content])


def add_download_link():
    with open(dbfile, "rb") as fp:
        btn = st.download_button(label="下载标注结果(sqlite3 db 文件)",
                                 data=fp,
                                 file_name="labelled_tag.db",
                                 mime="application/octet-stream")
    conn = sqlite3.connect(dbfile,
                           isolation_level=None,
                           detect_types=sqlite3.PARSE_COLNAMES)
    db_df = pd.read_sql_query("SELECT * FROM tags", conn)
    db_df.to_csv('labelled_tag.csv', index=False)
    with open("labelled_tag.csv", "rb") as fp:
        btn = st.download_button(label="下载标注结果(csv 文件)",
                                 data=fp,
                                 file_name="labelled_tag.csv",
                                 mime="application/octet-stream")


def reload_corpus(sample_file: str, label_file: str):
    # Get new files
    sf = cf_force(sample_file)
    lf = cf_force(label_file)
    corpus = cf.io.read(sf).data
    targets = sorted(list(set(cf.io.read(lf).data)))
    return corpus, targets


def clean_corpus(sample_file: str, label_file: str):
    # Get new files
    sf = '/tmp/' + sample_file
    lf = '/tmp/' + label_file
    os.remove(sf)
    os.remove(lf)


def classification_label(sample_file: str, label_file: str):
    samples, labels = reload_corpus(sample_file, label_file)
    # label for classification tasks
    register = st.empty()
    theend = st.empty()
    para_list = [[format(x) for x in s.split('\n')] for s in samples]
    is_done = False

    while True:
        num = st.session_state.num
        if num >= len(para_list):
            is_done = True
        else:
            para = para_list[num]

        if is_done or theend.button('DONE', key=num):
            theend.empty()
            st.write(':thumbsup: thanks!')
            st.markdown('### result')
            df = pd.DataFrame(st.session_state.data)
            st.dataframe(df, width=1610)
            add_download_link()
            clean_corpus(sample_file, label_file)
            break
        else:
            with register.form(key=str(num)):

                new_tag = NewSample(num, para, labels)
                if st.form_submit_button(f'submit {num+1}/{len(para_list)}'):
                    st.session_state.data.append({
                        # 'id': num,
                        'target': new_tag.target,
                        'content': new_tag.content,
                    })
                    new_tag.persist()
                    st.session_state.num += 1
                    register.empty()
                    theend.empty()
                else:
                    st.stop()


if __name__ == '__main__':
    sample_file = 'sample_file.txt'
    label_file = 'label_file.txt'
    classification_label(sample_file, label_file)
