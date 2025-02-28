import tkinter as tk
from tkinter import ttk, messagebox, colorchooser
import json
import random
import requests
import os
import sys

CURRENT_VERSION = "1.0.0"

DEFAULT_COLORS = {
    "蓝色": {"weight": 50, "color": "#3399FF"},
    "紫色": {"weight": 30, "color": "#CC99FF"},
    "金色": {"weight": 20, "color": "#FFD700"}
}

class LotteryApp:
    def __init__(self, root):
        self.root = root
        self.root.title("抽奖程序")
        self.data = []
        self.color_settings = {}
        self.filter_color = tk.StringVar(value="全部")
        self.sort_by = tk.StringVar(value="默认")
        self.sort_order = tk.StringVar(value="升序")
        self.last_selected = None
        
        self.setup_ui()
        self.load_data()
        self.setup_style()
        self.setup_menu()

    def setup_style(self):
        self.style = ttk.Style()
        self.style.configure("Treeview", rowheight=25)
        self.style.map("Treeview", background=[("selected", "#0000ff")])

    def setup_menu(self):
        menubar = tk.Menu(self.root)
        settings_menu = tk.Menu(menubar, tearoff=0)
        settings_menu.add_command(label="颜色设置", command=self.open_color_settings)
        settings_menu.add_separator()
        settings_menu.add_command(label="检查更新", command=check_for_updates)
        menubar.add_cascade(label="设置", menu=settings_menu)
        self.root.config(menu=menubar)

    def setup_ui(self):
        # 输入区域
        input_frame = ttk.Frame(self.root)
        input_frame.pack(pady=10, fill=tk.X)

        ttk.Label(input_frame, text="奖项名称:").grid(row=0, column=0, padx=5)
        self.name_entry = ttk.Entry(input_frame, width=15)
        self.name_entry.grid(row=0, column=1, padx=5)

        ttk.Label(input_frame, text="颜色分类:").grid(row=0, column=2, padx=5)
        self.color_combo = ttk.Combobox(input_frame, state="readonly", width=8)
        self.color_combo.grid(row=0, column=3, padx=5)

        ttk.Button(input_frame, text="添加", command=self.add_prize).grid(row=0, column=4, padx=5)

        # 控制面板
        control_frame = ttk.Frame(self.root)
        control_frame.pack(pady=5, fill=tk.X)

        ttk.Button(control_frame, text="删除选中", command=self.delete_selected).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="保存数据", command=self.auto_save).pack(side=tk.LEFT, padx=5)

        # 筛选和排序
        filter_frame = ttk.Frame(self.root)
        filter_frame.pack(pady=5, fill=tk.X)

        ttk.Label(filter_frame, text="筛选:").pack(side=tk.LEFT)
        filter_combo = ttk.Combobox(filter_frame, textvariable=self.filter_color, 
                                  values=["全部"] + list(self.color_settings.keys()), 
                                  state="readonly", width=8)
        filter_combo.pack(side=tk.LEFT, padx=5)
        filter_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh_tree())

        ttk.Label(filter_frame, text="排序:").pack(side=tk.LEFT, padx=(10,0))
        sort_combo = ttk.Combobox(filter_frame, textvariable=self.sort_by, 
                                values=["默认", "颜色", "权重", "概率"], state="readonly", width=8)
        sort_combo.pack(side=tk.LEFT)
        sort_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh_tree())

        ttk.Combobox(filter_frame, textvariable=self.sort_order, 
                   values=["升序", "降序"], state="readonly", width=6).pack(side=tk.LEFT, padx=5)
        self.sort_order.trace_add("write", lambda *args: self.refresh_tree())

        # 奖池列表
        self.tree = ttk.Treeview(self.root, columns=("checked", "name", "color", "weight", "probability"), 
                               show="headings", selectmode="browse")
        self.tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        columns = {
            "checked": {"text": "✓", "width": 30},
            "name": {"text": "奖项名称", "width": 120},
            "color": {"text": "颜色", "width": 80},
            "weight": {"text": "权重", "width": 80},
            "probability": {"text": "概率", "width": 100}
        }

        for col, config in columns.items():
            self.tree.heading(col, text=config["text"])
            self.tree.column(col, width=config["width"], anchor="center")

        self.tree.bind("<Button-1>", self.on_tree_click)

        # 抽奖区域
        result_frame = ttk.Frame(self.root)
        result_frame.pack(pady=10, fill=tk.X)

        ttk.Button(result_frame, text="开始抽奖", command=self.draw_lottery).pack(side=tk.LEFT, padx=5)
        self.result_label = ttk.Label(result_frame, text="", font=("Arial", 12))
        self.result_label.pack(side=tk.LEFT, padx=10)

    def update_color_combo(self):
        self.color_combo["values"] = list(self.color_settings.keys())
        if self.color_combo["values"]:
            self.color_combo.current(0)

    def add_prize(self):
        name = self.name_entry.get().strip()
        color = self.color_combo.get()
        
        if not name:
            messagebox.showwarning("错误", "请输入奖项名称")
            return
        if not color:
            messagebox.showwarning("错误", "请选择颜色分类")
            return
            
        self.data.append({
            "name": name,
            "color": color,
            "checked": True
        })
        self.name_entry.delete(0, tk.END)
        self.refresh_tree()
        self.auto_save()

    def delete_selected(self):
        selected = self.tree.selection()
        if not selected:
            return
            
        index = self.tree.index(selected[0])
        del self.data[index]
        self.refresh_tree()
        self.auto_save()

    def on_tree_click(self, event):
        region = self.tree.identify("region", event.x, event.y)
        if region == "cell":
            column = self.tree.identify_column(event.x)
            item = self.tree.identify_row(event.y)
            if column == "#1":  # 勾选列
                index = self.tree.index(item)
                self.data[index]["checked"] = not self.data[index]["checked"]
                self.refresh_tree()
                self.auto_save()

    def refresh_tree(self):
        # 更新颜色标签
        for color_name, config in self.color_settings.items():
            self.tree.tag_configure(config["color"], background=config["color"])
        
        # 计算真实概率
        total_weight = sum(self.color_settings[item["color"]]["weight"] 
                          for item in self.data if item["checked"])
        
        for item in self.data:
            if total_weight == 0 or not item["checked"]:
                item["probability"] = 0.0
            else:
                item["probability"] = (self.color_settings[item["color"]]["weight"] 
                                      / total_weight)

        # 应用筛选
        filter_color = self.filter_color.get()
        filtered = [item for item in self.data 
                   if filter_color == "全部" or item["color"] == filter_color]

        # 应用排序
        sort_key = self.sort_by.get()
        reverse = self.sort_order.get() == "降序"
        
        if sort_key == "颜色":
            color_order = {color: idx for idx, color in enumerate(self.color_settings)}
            filtered.sort(key=lambda x: color_order[x["color"]], reverse=reverse)
        elif sort_key == "权重":
            filtered.sort(key=lambda x: self.color_settings[x["color"]]["weight"], reverse=reverse)
        elif sort_key == "概率":
            filtered.sort(key=lambda x: x["probability"], reverse=reverse)

        # 更新Treeview
        self.tree.delete(*self.tree.get_children())
        
        for item in filtered:
            checked = "✓" if item["checked"] else ""
            color_config = self.color_settings[item["color"]]
            prob = item["probability"]
            self.tree.insert("", "end", values=(
                checked,
                item["name"],
                item["color"],
                color_config["weight"],
                f"{prob:.2%}" if prob > 0 else "0.00%"
            ), tags=(color_config["color"],))

    def draw_lottery(self):
        candidates = [item for item in self.data if item["checked"]]
        if not candidates:
            messagebox.showwarning("错误", "没有可抽选的奖项")
            return
        
        if len(candidates) == 1:
            selected = candidates[0]
        else:
            weights = [self.color_settings[item["color"]]["weight"] for item in candidates]
            while True:
                selected = random.choices(candidates, weights=weights, k=1)[0]
                if self.last_selected is None or selected != self.last_selected:
                    break
        
        
        self.last_selected = selected
        self.result_label.config(text=f"中奖结果：{selected['name']} ({selected['color']})")

    def auto_save(self):
        try:
            save_data = {
                "colors": self.color_settings,
                "items": self.data
            }
            with open("data.json", "w", encoding="utf-8") as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            messagebox.showerror("保存失败", f"自动保存失败：{str(e)}")

    def load_data(self):
        try:
            with open("data.json", "r", encoding="utf-8") as f:
                save_data = json.load(f)
                self.color_settings = save_data.get("colors", DEFAULT_COLORS)
                self.data = save_data.get("items", [])
                self.update_color_combo()
                self.refresh_tree()
        except FileNotFoundError:
            self.color_settings = dict(DEFAULT_COLORS)
            self.update_color_combo()
        except Exception as e:
            messagebox.showerror("加载失败", f"加载数据失败：{str(e)}")

    def open_color_settings(self):
        ColorSettingsWindow(self.root, self)

class ColorSettingsWindow(tk.Toplevel):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.title("颜色设置")
        self.geometry("500x400")
        
        self.create_widgets()
        self.load_colors()

    def create_widgets(self):
        # 颜色列表
        self.tree = ttk.Treeview(self, columns=("name", "weight", "color"), show="headings")
        self.tree.heading("name", text="颜色名称")
        self.tree.heading("weight", text="权重")
        self.tree.heading("color", text="颜色值")
        self.tree.column("name", width=120)
        self.tree.column("weight", width=80)
        self.tree.column("color", width=100)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # 操作按钮
        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=5)
        
        ttk.Button(btn_frame, text="添加", command=self.add_color).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="删除", command=self.delete_color).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="保存", command=self.save_colors).pack(side=tk.LEFT, padx=2)

    def load_colors(self):
        self.tree.delete(*self.tree.get_children())
        for name, config in self.app.color_settings.items():
            self.tree.insert("", "end", values=(
                name, 
                config["weight"],
                config["color"]
            ))

    def add_color(self):
        AddColorWindow(self, self.app)

    def delete_color(self):
        selected = self.tree.selection()
        if not selected:
            return
            
        item = self.tree.item(selected[0])
        color_name = item["values"][0]
        del self.app.color_settings[color_name]
        self.load_colors()

    def save_colors(self):
        self.app.update_color_combo()
        self.app.refresh_tree()
        self.app.auto_save()
        self.destroy()

class AddColorWindow(tk.Toplevel):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.title("添加颜色")
        self.geometry("300x150")
        
        self.create_widgets()

    def create_widgets(self):
        frame = ttk.Frame(self)
        frame.pack(pady=10, padx=10, fill=tk.X)

        ttk.Label(frame, text="颜色名称:").grid(row=0, column=0, sticky="w")
        self.name_entry = ttk.Entry(frame)
        self.name_entry.grid(row=0, column=1, padx=5)

        ttk.Label(frame, text="权重:").grid(row=1, column=0, sticky="w")
        self.weight_entry = ttk.Entry(frame, validate="key")
        self.weight_entry.grid(row=1, column=1, padx=5)
        self.weight_entry["validatecommand"] = (self.register(self.validate_weight), "%P")

        ttk.Label(frame, text="颜色值:").grid(row=2, column=0, sticky="w")
        self.color_entry = ttk.Entry(frame)
        self.color_entry.grid(row=2, column=1, padx=5)
        ttk.Button(frame, text="选择", command=self.choose_color).grid(row=2, column=2)

        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=5)
        ttk.Button(btn_frame, text="确定", command=self.save_color).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="取消", command=self.destroy).pack(side=tk.LEFT)

    def validate_weight(self, value):
        return value.isdigit() or value == ""

    def choose_color(self):
        color = colorchooser.askcolor()[1]
        if color:
            self.color_entry.delete(0, tk.END)
            self.color_entry.insert(0, color)

    def save_color(self):
        name = self.name_entry.get().strip()
        weight = self.weight_entry.get()
        color = self.color_entry.get().strip()

        if not name or not weight or not color:
            messagebox.showwarning("错误", "请填写所有字段")
            return
            
        if name in self.app.color_settings:
            messagebox.showwarning("错误", "颜色名称已存在")
            return
            
        self.app.color_settings[name] = {
            "weight": int(weight),
            "color": color
        }
        self.destroy()
        self.master.load_colors()

def check_for_updates():
    try:
        # 从服务器获取最新版本信息
        version_url = "https://raw.githubusercontent.com/Voller-u/Spinner/master/version.json"
        response = requests.get(version_url)
        version_info = response.json()
        
        latest_version = version_info["version"]
        download_url = version_info["download_url"]
        
        # 解析版本号进行比较
        current_parts = [int(x) for x in CURRENT_VERSION.split(".")]
        latest_parts = [int(x) for x in latest_version.split(".")]
        
        needs_update = False
        for current, latest in zip(current_parts, latest_parts):
            if latest > current:
                needs_update = True
                break
            elif current > latest:
                break
        
        if needs_update:
            if messagebox.askyesno("更新可用", 
                f"发现新版本 {latest_version}\n当前版本 {CURRENT_VERSION}\n是否更新？"):
                download_and_replace(download_url)
        else:
            messagebox.showinfo("检查更新", "当前已是最新版本！")
            
    except Exception as e:
        messagebox.showerror("更新检查失败", f"检查更新失败：{str(e)}")

def download_and_replace(download_url):
    try:
        response = requests.get(download_url)
        response.raise_for_status()
        
        # 获取当前脚本路径
        current_script = os.path.abspath(__file__)
        
        # 创建备份
        backup_path = current_script + ".backup"
        os.replace(current_script, backup_path)
        
        # 保存新文件
        try:
            with open(current_script, 'wb') as f:
                f.write(response.content)
            
            # 更新成功后删除备份
            os.remove(backup_path)
            
            if messagebox.askyesno("更新完成", "程序已更新，需要重启才能生效。是否立即重启？"):
                python = sys.executable
                os.execl(python, python, *sys.argv)
                
        except Exception as e:
            # 如果保存新文件失败，恢复备份
            if os.path.exists(backup_path):
                os.replace(backup_path, current_script)
            raise e
            
    except Exception as e:
        messagebox.showerror("更新失败", f"更新失败：{str(e)}")

if __name__ == "__main__":
    root = tk.Tk()
    app = LotteryApp(root)
    root.geometry("1000x700")
    root.mainloop()