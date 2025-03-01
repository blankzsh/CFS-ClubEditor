import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3
import json
from PIL import Image, ImageTk

class TeamDatabaseViewer(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("CFS球队编辑器 BY.卡尔纳斯")
        self.geometry("800x600")
        self.minsize(750, 550)
        self.iconbitmap("favicon.ico")  # 图标路径
        # 初始化数据
        self.fields = [
            "ID", "TeamName", "TeamWealth", "TeamFoundYear",
            "TeamLocation", "SupporterCount", "StadiumName", "Nickname", "BelongingLeague"
        ]
        self.field_labels = {
            "ID": "编号",
            "BelongingLeague": "联赛ID",
            "TeamName": "球队名称",
            "TeamWealth": "球队财富（万）",
            "TeamFoundYear": "成立年份",
            "TeamLocation": "所在地区",
            "SupporterCount": "支持者数量",
            "StadiumName": "主场名称",
            "Nickname": "球队昵称",
        }
        self.team_records = []
        self.displayed_team_records = []
        self.staff_records = []
        self.conn = None
        self.cursor = None
        self.current_team_id = None
        self.current_search = ""
        self.db_directory = ""
        self.logo_image = None
        self.leagues = {}  # 存储联赛名称的字典
        self.temp_data = {}  # 用于存储未保存的修改

        # 创建界面
        self.create_widgets()

    def create_widgets(self):
        """创建界面组件"""
        self.main_frame = ttk.Frame(self)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 控制面板
        control_frame = ttk.Frame(self.main_frame)
        control_frame.pack(fill=tk.X, pady=5)

        ttk.Button(control_frame, text="加载数据库", command=self.load_database).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="保存球队修改", command=self.save_team_changes).pack(side=tk.LEFT, padx=5)

        # 搜索功能
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(control_frame, textvariable=self.search_var, width=25)
        search_entry.pack(side=tk.LEFT, padx=10)
        search_entry.bind("<Return>", lambda event: self.search())
        ttk.Button(control_frame, text="搜索", command=self.search).pack(side=tk.LEFT)

        # 主内容区
        content_frame = ttk.Frame(self.main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True)

        # 球队列表（添加滚动条）
        list_frame = ttk.Frame(content_frame, width=200)
        list_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5)

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL)
        self.listbox = tk.Listbox(list_frame, width=25, yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.listbox.yview)

        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.listbox.bind('<<ListboxSelect>>', self.on_select)

        # 详细信息面板
        detail_frame = ttk.Frame(content_frame)
        detail_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)

        # Logo显示区域
        self.logo_frame = ttk.Frame(detail_frame)
        self.logo_frame.pack(fill=tk.X, pady=5)
        self.logo_label = ttk.Label(self.logo_frame)
        self.logo_label.pack()

        # 球队信息字段
        self.entries = {}
        for field in self.fields[:-1]:  # 不显示 LeagueID
            row = ttk.Frame(detail_frame)
            row.pack(fill=tk.X, pady=2)
            ttk.Label(row, text=self.field_labels[field], width=12).pack(side=tk.LEFT)
            entry = ttk.Entry(row)
            entry.pack(fill=tk.X, expand=True)
            self.entries[field] = entry

        # 联赛名称显示
        league_row = ttk.Frame(detail_frame)
        league_row.pack(fill=tk.X, pady=2)
        ttk.Label(league_row, text="所在联赛：", width=12).pack(side=tk.LEFT)
        self.league_label = ttk.Label(league_row, text="")
        self.league_label.pack(side=tk.LEFT)

        # 员工信息表格
        staff_frame = ttk.Labelframe(detail_frame, text="员工信息")
        staff_frame.pack(fill=tk.X, pady=10)
        self.staff_tree = ttk.Treeview(staff_frame, columns=("ID", "姓名", "能力值", "知名度"),
                                       show="headings")
        for col in ("ID", "姓名", "能力值", "知名度"):
            self.staff_tree.heading(col, text=col)
            self.staff_tree.column(col, width=80, anchor=tk.CENTER)
        self.staff_tree.pack(fill=tk.X)
        self.staff_tree.bind("<Double-1>", self.edit_staff)

        # 状态栏
        self.status_var = tk.StringVar()
        ttk.Label(self.main_frame, textvariable=self.status_var, relief=tk.SUNKEN).pack(fill=tk.X)

    def load_database(self):
        """加载数据库文件"""
        try:
            path = filedialog.askopenfilename(filetypes=[("SQLite 数据库", "*.db"), ("所有文件", "*.*")])
            if not path:
                return

            self.db_directory = os.path.dirname(path)
            if self.conn:
                self.conn.close()
            self.conn = sqlite3.connect(path)
            self.cursor = self.conn.cursor()

            # 加载联赛信息
            self.cursor.execute("SELECT ID, LeagueName FROM League")
            leagues = self.cursor.fetchall()
            self.leagues = {l[0]: l[1] for l in leagues}

            self.refresh_team_data()
            self.refresh_staff_data()
            self.status_var.set(f"已加载数据库：{path}")
            messagebox.showinfo("成功", "数据库加载成功！")

        except Exception as e:
            messagebox.showerror("错误", f"数据库加载失败：{str(e)}")

    def refresh_team_data(self):
        """刷新球队数据"""
        query = """
            SELECT T.ID, T.TeamName, T.TeamWealth, T.TeamFoundYear,
                   T.TeamLocation, T.SupporterCount, T.StadiumName, 
                   T.Nickname, T.BelongingLeague
            FROM Teams T
        """
        self.cursor.execute(query)
        self.team_records = self.cursor.fetchall()
        self.apply_search_filter()
        self.refresh_list()

    def refresh_staff_data(self):
        """刷新员工数据"""
        self.cursor.execute("SELECT ID, Name, AbilityJSON, Fame, EmployedTeamID FROM Staff")
        self.staff_records = self.cursor.fetchall()

    def on_select(self, event):
        """处理列表选择事件"""
        try:
            idx = self.listbox.curselection()[0]
            record = self.displayed_team_records[idx]
            self.current_team_id = record[0]

            self.update_logo(self.current_team_id)

            # 如果当前球队有临时数据，则加载临时数据
            if self.current_team_id in self.temp_data:
                data = self.temp_data[self.current_team_id]
                for field in self.fields[:-2]:  # 不保存 LeagueID
                    self.entries[field].delete(0, tk.END)
                    self.entries[field].insert(0, str(data.get(field, "")))
            else:
                # 否则加载数据库中的数据
                for field in self.fields[:-1]:  # 遍历所有字段（除BelongingLeague）
                    if field == "BelongingLeague":  # 跳过联赛ID字段
                        continue
                    idx_in_record = self.fields.index(field)
                    self.entries[field].delete(0, tk.END)
                    self.entries[field].insert(0, str(record[idx_in_record]))

            league_name = self.leagues.get(record[-1], "未知联赛")
            self.league_label.config(text=league_name)

            self.update_staff(self.current_team_id)  # 正确传递球队ID

        except IndexError:
            pass

    def update_logo(self, team_id):
        """更新球队Logo显示"""
        if self.logo_image:
            self.logo_image = None

        if team_id:
            logo_path = os.path.join(self.db_directory, f"L{team_id}.png")
            if os.path.exists(logo_path):
                try:
                    img = Image.open(logo_path)
                    img = img.resize((128, 128), Image.Resampling.LANCZOS)
                    self.logo_image = ImageTk.PhotoImage(img)
                    self.logo_label.config(image=self.logo_image)
                    # 绑定点击事件
                    self.logo_label.bind("<Button-1>", lambda event: self.replace_logo(team_id))
                    return
                except Exception as e:
                    print(f"加载Logo失败：{str(e)}")

        self.logo_label.config(image='')

    def replace_logo(self, team_id):
        """替换Logo"""
        if not team_id:
            messagebox.showwarning("警告", "请先选择一个球队")
            return

        # 弹出文件选择框
        file_path = filedialog.askopenfilename(
            filetypes=[("图片文件", "*.png;*.jpg;*.jpeg;*.bmp;*.gif")]
        )
        if not file_path:
            return

        # 检查文件格式并转换为PNG
        try:
            img = Image.open(file_path)
            logo_path = os.path.join(self.db_directory, f"L{team_id}.png")
            img.save(logo_path, "PNG")
            self.update_logo(team_id)
            messagebox.showinfo("成功", "Logo已替换")
        except Exception as e:
            messagebox.showerror("错误", f"替换Logo失败：{str(e)}")

    def save_team_changes(self):
        """保存球队信息修改"""
        if not self.conn:
            messagebox.showwarning("警告", "请先加载数据库")
            return

        try:
            if not self.current_team_id:
                messagebox.showwarning("警告", "请选择要修改的记录")
                return

            # 获取当前修改的数据
            data = {}
            for field in self.fields[:-2]:  # 不保存 LeagueID
                value = self.entries[field].get()
                if field in ["TeamWealth", "SupporterCount", "TeamFoundYear"]:
                    try:
                        data[field] = self.validate_number(value, self.field_labels[field])
                    except ValueError:
                        return  # 如果验证失败，直接返回
                else:
                    data[field] = value

            # 提示用户确认保存
            confirm = messagebox.askyesno("确认保存", "您确定要保存对球队数据的修改吗？")
            if not confirm:
                return

            # 执行保存操作
            self.cursor.execute(f"""
                UPDATE Teams SET
                    {','.join([f"{field}=?" for field in self.fields[:-2]])}
                WHERE ID = ?
            """, [data[field] for field in self.fields[:-2]] + [self.current_team_id])

            self.conn.commit()

            # 清空临时数据
            self.temp_data.pop(self.current_team_id, None)

            # 刷新球队数据
            self.refresh_team_data()

            # 重新选择当前球队
            self.select_current_team()

            messagebox.showinfo("成功", "球队数据已保存")

        except Exception as e:
            messagebox.showerror("错误", f"保存失败：{str(e)}")

    def search(self):
        """执行搜索"""
        self.current_search = self.search_var.get()
        self.apply_search_filter()
        self.refresh_list()

    def apply_search_filter(self):
        """应用当前搜索条件"""
        filtered = []
        for record in self.team_records:
            record_str = ''.join(map(str, record))
            if self.current_search.lower() in record_str.lower():
                filtered.append(record)
        self.displayed_team_records = filtered

    def refresh_list(self):
        """刷新列表显示"""
        self.listbox.delete(0, tk.END)
        for record in self.displayed_team_records:
            display_str = f"{record[1]} ({record[0]})"
            if record[-1] in self.leagues:
                display_str += f" - {self.leagues[record[-1]]}"
            self.listbox.insert(tk.END, display_str)

    def select_current_team(self):
        """重新选择当前球队"""
        if self.current_team_id:
            self.listbox.selection_clear(0, tk.END)
            for i, record in enumerate(self.displayed_team_records):
                if record[0] == self.current_team_id:
                    self.listbox.selection_set(i)
                    self.listbox.see(i)
                    break

    def update_staff(self, team_id):
        """更新员工信息显示"""
        for item in self.staff_tree.get_children():
            self.staff_tree.delete(item)

        # 强制转为字符串比较（根据实际数据库类型调整）
        staff = [s for s in self.staff_records if str(s[4]) == str(team_id)]

        # 显示所有员工（移除切片）
        for s in staff:  # 原代码为 staff[:2]
            try:
                ability = json.loads(s[2]).get('rawAbility', 0)
            except (json.JSONDecodeError, AttributeError):
                ability = 0

            self.staff_tree.insert('', 'end', values=(
                s[0], s[1], ability, s[3]
            ))

    def edit_staff(self, event):
        """编辑员工信息"""
        selected = self.staff_tree.selection()
        if not selected:
            return

        item = self.staff_tree.item(selected)
        staff_id = item['values'][0]

        staff_record = next((s for s in self.staff_records if str(s[0]) == staff_id), None)
        if not staff_record:
            return
        (s_id, s_name, s_ability_json, s_fame, s_team_id) = staff_record

        edit_win = tk.Toplevel(self)
        edit_win.title("编辑员工信息")
        edit_win.geometry("300x200")

        fields = ["姓名", "能力值", "知名度"]
        entries = {}
        for i, (name, data) in enumerate(zip(fields, [s_name, s_fame, s_fame])):
            row = ttk.Frame(edit_win)
            row.pack(fill=tk.X, padx=5, pady=5)
            ttk.Label(row, text=f"{name}：").pack(side=tk.LEFT, fill=tk.Y)
            entry = ttk.Entry(row)
            entry.insert(0, str(data))
            entry.pack(side=tk.RIGHT, fill=tk.X, expand=True)
            entries[name] = entry

        def save_changes():
            try:
                new_name = entries["姓名"].get()
                new_ability = entries["能力值"].get()
                new_fame = entries["知名度"].get()

                ability_data = json.dumps({"rawAbility": int(new_ability)})

                self.cursor.execute("""
                    UPDATE Staff SET
                        Name = ?,
                        Fame = ?,
                        AbilityJSON = ?
                    WHERE ID = ?
                """, (new_name, new_fame, ability_data, s_id))
                self.conn.commit()

                self.refresh_staff_data()
                self.update_staff(s_team_id)
                edit_win.destroy()
                messagebox.showinfo("成功", "员工信息已更新")

            except ValueError:
                messagebox.showerror("错误", "请输入有效的数字")
            except Exception as e:
                messagebox.showerror("错误", f"更新失败：{str(e)}")

        ttk.Button(edit_win, text="保存", command=save_changes).pack(fill=tk.X, padx=5, pady=10)

    def validate_number(self, value, field_name):
        """验证数字输入"""

        try:
            return float(value) if '.' in value else int(value)
        except ValueError:
            messagebox.showerror("输入错误", f"{field_name} 必须为数字")
            raise

    def __del__(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()


if __name__ == "__main__":
    app = TeamDatabaseViewer()
    app.mainloop()
