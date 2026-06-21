# 采油厂油水井作业成本管理系统 - Flask 后端
import sys, os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify

app = Flask(__name__)
app.secret_key = 'zyxt_oilfield_2024'

# ── 数据库 ──────────────────────────────────
def get_db():
    import pyodbc
    conn_str = (
        'DRIVER={ODBC Driver 17 for SQL Server};'
        'SERVER=KILIN\\SQLEXPRESS;'
        'DATABASE=zyxt;'
        'Trusted_Connection=yes;'
        'TrustServerCertificate=yes;'
    )
    return pyodbc.connect(conn_str)

def query_dict(sql, params=None):
    conn = get_db()
    cursor = conn.cursor()
    if params: cursor.execute(sql, params)
    else: cursor.execute(sql)
    cols = [col[0] for col in cursor.description] if cursor.description else []
    rows = cursor.fetchall()
    conn.close()
    return [dict(zip(cols, row)) for row in rows]

def execute(sql, params=None):
    conn = get_db()
    cursor = conn.cursor()
    try:
        if params: cursor.execute(sql, params)
        else: cursor.execute(sql)
        conn.commit(); return True
    except Exception as e:
        conn.rollback(); raise e
    finally: conn.close()

# ── 首页仪表盘 ──────────────────────────────
@app.route('/')
def index():
    try:
        stats = {
            '项目数': query_dict("SELECT COUNT(*) AS cnt FROM 成本消耗表")[0]['cnt'],
            '材料记录': query_dict("SELECT COUNT(*) AS cnt FROM 材料消耗表")[0]['cnt'],
            '油水井数': query_dict("SELECT COUNT(*) AS cnt FROM 油水井表")[0]['cnt'],
            '单位数': query_dict("SELECT COUNT(*) AS cnt FROM 单位代码表")[0]['cnt'],
        }
        recent = query_dict("SELECT TOP 5 * FROM 成本消耗表 ORDER BY 预算日期 DESC")

        # 各施工单位结算金额汇总（供图表用）
        chart_data = query_dict(
            "SELECT 施工单位, SUM(结算金额) AS 合计 FROM 成本消耗表 GROUP BY 施工单位"
        )

        # 各施工内容数量统计
        content_stats = query_dict(
            "SELECT 施工内容, COUNT(*) AS 次数 FROM 成本消耗表 GROUP BY 施工内容"
        )
    except Exception as e:
        return render_template('index.html', error=str(e))

    return render_template('index.html', stats=stats, recent=recent,
                           chart_data=chart_data, content_stats=content_stats)

# ── 项目列表 ─────────────────────────────────
@app.route('/projects')
def projects():
    kw = request.args.get('keyword','')
    if kw:
        rows = query_dict(
            "SELECT * FROM 成本消耗表 WHERE 单据号 LIKE ? OR 预算单位 LIKE ? OR 施工单位 LIKE ? ORDER BY 预算日期 DESC",
            (f'%{kw}%',f'%{kw}%',f'%{kw}%'))
    else:
        rows = query_dict("SELECT * FROM 成本消耗表 ORDER BY 预算日期 DESC")
    return render_template('projects.html', rows=rows, keyword=kw)

# ── 新增 / 编辑 ──────────────────────────────
@app.route('/projects/add', methods=['GET','POST'])
def add_project():
    units = query_dict("SELECT * FROM 单位代码表")
    wells = query_dict("SELECT * FROM 油水井表")
    ctors = query_dict("SELECT * FROM 施工单位表")
    if request.method == 'POST':
        try:
            d = request.form
            execute(
                "INSERT INTO 成本消耗表(单据号,预算单位,井号,预算金额,预算人,预算日期,开工日期,完工日期,施工单位,施工内容,材料费,人工费,设备费,其他费用,结算金额,结算人,结算日期) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (d['单据号'],d['预算单位'],d['井号'],float(d['预算金额']),d['预算人'],d['预算日期'],
                 d['开工日期'],d['完工日期'],d['施工单位'],d['施工内容'],
                 float(d['材料费']),float(d['人工费']),float(d['设备费']),float(d['其他费用']),
                 float(d['结算金额']),d['结算人'],d['结算日期']))
            flash('新增成功！','success'); return redirect(url_for('projects'))
        except Exception as e: flash(f'新增失败：{e}','danger')
    return render_template('project_form.html', units=units, wells=wells, ctors=ctors, row=None, mode='新增')

@app.route('/projects/edit/<id>', methods=['GET','POST'])
def edit_project(id):
    units = query_dict("SELECT * FROM 单位代码表")
    wells = query_dict("SELECT * FROM 油水井表")
    ctors = query_dict("SELECT * FROM 施工单位表")
    if request.method == 'POST':
        try:
            d = request.form
            execute(
                "UPDATE 成本消耗表 SET 预算单位=?,井号=?,预算金额=?,预算人=?,预算日期=?,开工日期=?,完工日期=?,施工单位=?,施工内容=?,材料费=?,人工费=?,设备费=?,其他费用=?,结算金额=?,结算人=?,结算日期=? WHERE 单据号=?",
                (d['预算单位'],d['井号'],float(d['预算金额']),d['预算人'],d['预算日期'],
                 d['开工日期'],d['完工日期'],d['施工单位'],d['施工内容'],
                 float(d['材料费']),float(d['人工费']),float(d['设备费']),float(d['其他费用']),
                 float(d['结算金额']),d['结算人'],d['结算日期'], id))
            flash('修改成功！','success'); return redirect(url_for('projects'))
        except Exception as e: flash(f'修改失败：{e}','danger')
    row = query_dict("SELECT * FROM 成本消耗表 WHERE 单据号=?",(id,))
    if not row: flash('记录不存在','danger'); return redirect(url_for('projects'))
    return render_template('project_form.html', units=units, wells=wells, ctors=ctors, row=row[0], mode='编辑')

@app.route('/projects/delete/<id>', methods=['POST'])
def delete_project(id):
    try:
        execute("DELETE FROM 成本消耗表 WHERE 单据号=?",(id,))
        flash('删除成功！','success')
    except Exception as e: flash(f'删除失败：{e}','danger')
    return redirect(url_for('projects'))

# ── 材料明细 ─────────────────────────────────
@app.route('/materials')
def materials():
    rows = query_dict("""SELECT a.*, b.名称规格, b.计量单位
        FROM 材料消耗表 a JOIN 物码表 b ON a.物码 = b.物码 ORDER BY a.单据号""")
    return render_template('materials.html', rows=rows)

# ── 成本报表 ─────────────────────────────────
@app.route('/report', methods=['GET','POST'])
def report():
    result = None
    units = query_dict("SELECT * FROM 单位代码表")
    if request.method == 'POST':
        try:
            unit = request.form['单位代码']; sd = request.form['起始日期']; ed = request.form['结束日期']
            unit_name = query_dict("SELECT 单位名称 FROM 单位代码表 WHERE 单位代码=?",(unit,))[0]['单位名称']
            # 如果是父级单位，匹配所有子单位
            data = query_dict("""
                SELECT SUM(预算金额) AS 预算金额, SUM(结算金额) AS 结算金额,
                       SUM(入账金额) AS 入账金额,
                       SUM(预算金额)-SUM(结算金额) AS 未结算,
                       SUM(结算金额)-SUM(入账金额) AS 未入账
                FROM 成本消耗表 WHERE 预算单位 LIKE ? AND 预算日期>=? AND 预算日期<=?""",
                (unit + '%', sd, ed))
            if data and data[0]['预算金额'] is not None:
                result = data[0]
                result['单位名称'] = unit_name
                result['起始日期'] = sd; result['结束日期'] = ed
            else:
                flash(f'{unit_name} 在 {sd} ~ {ed} 期间没有数据','warning')
        except Exception as e: flash(f'报表生成失败：{e}','danger')
    return render_template('report.html', units=units, result=result)

# ── 图表数据 API ─────────────────────────────
@app.route('/api/chart/cost_by_unit')
def chart_cost_by_unit():
    data = query_dict("SELECT 预算单位, SUM(结算金额) AS total FROM 成本消耗表 GROUP BY 预算单位")
    return jsonify(data)

@app.route('/api/chart/cost_by_content')
def chart_cost_by_content():
    data = query_dict("SELECT 施工内容, COUNT(*) AS cnt FROM 成本消耗表 GROUP BY 施工内容")
    return jsonify(data)

@app.route('/api/chart/monthly')
def chart_monthly():
    data = query_dict("""
        SELECT FORMAT(预算日期,'yyyy-MM') AS month, SUM(结算金额) AS total
        FROM 成本消耗表 GROUP BY FORMAT(预算日期,'yyyy-MM') ORDER BY month""")
    return jsonify(data)

# ── 启动 ─────────────────────────────────────
if __name__ == '__main__':
    print('  [油田成本管理系统 v2.0]')
    print('  访问 -> http://127.0.0.1:5000')
    app.run(debug=True, host='127.0.0.1', port=5000)
