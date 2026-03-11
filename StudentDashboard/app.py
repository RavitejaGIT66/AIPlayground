from flask import Flask, render_template, request, jsonify
import pyodbc
import pandas as pd

app = Flask(__name__)

# ── Load & map data once at startup ──────────────────────────────────────────
def load_data():
    conn = pyodbc.connect(
        "DRIVER={ODBC Driver 17 for SQL Server};"
        "SERVER=localhost;"
        "DATABASE=sqldemo;"
        "Trusted_Connection=yes;",
        autocommit=True
    )
    df = pd.read_sql("SELECT * FROM dbo.Student_performance_data", conn)
    conn.close()

    df['Gender']            = df['Gender'].map({0: 'Male', 1: 'Female'})
    df['Ethnicity']         = df['Ethnicity'].map({0: 'Caucasian', 1: 'African American', 2: 'Asian', 3: 'Other'})
    df['ParentalEducation'] = df['ParentalEducation'].map({0: 'None', 1: 'High School', 2: 'Some College', 3: "Bachelor's", 4: 'Higher'})
    df['ParentalSupport']   = df['ParentalSupport'].map({0: 'None', 1: 'Low', 2: 'Moderate', 3: 'High', 4: 'Very High'})
    df['GradeClass']        = df['GradeClass'].map({0: 'A', 1: 'B', 2: 'C', 3: 'D', 4: 'F'})
    for col in ['Tutoring', 'Extracurricular', 'Sports', 'Music', 'Volunteering']:
        df[col] = df[col].map({0: 'No', 1: 'Yes'})
    return df

DF = load_data()

GRADE_ORDER = ['A', 'B', 'C', 'D', 'F']
EDU_ORDER   = ['None', 'High School', 'Some College', "Bachelor's", 'Higher']
SUP_ORDER   = ['None', 'Low', 'Moderate', 'High', 'Very High']

# ── Filter helper ─────────────────────────────────────────────────────────────
def filter_df(gender, ethnicity, grade, edu):
    d = DF.copy()
    if gender    != 'All': d = d[d['Gender']            == gender]
    if ethnicity != 'All': d = d[d['Ethnicity']         == ethnicity]
    if grade     != 'All': d = d[d['GradeClass']        == grade]
    if edu       != 'All': d = d[d['ParentalEducation'] == edu]
    return d

# ── Highlights builder ────────────────────────────────────────────────────────
def build_highlights(d):
    highlights = []

    # 1. Student count
    highlights.append({
        'label': 'Total Students',
        'value': f"{len(d):,}",
        'detail': f"{len(d)/len(DF)*100:.1f}% of full dataset",
        'tag': 'info'
    })

    # 2. Average GPA
    avg_gpa = d['GPA'].mean()
    overall_gpa = DF['GPA'].mean()
    delta = avg_gpa - overall_gpa
    highlights.append({
        'label': 'Average GPA',
        'value': f"{avg_gpa:.2f}",
        'detail': f"{'▲' if delta >= 0 else '▼'} {abs(delta):.2f} vs overall average ({overall_gpa:.2f})",
        'tag': 'up' if delta >= 0 else 'down'
    })

    # 3. Grade class breakdown
    top_grade = d['GradeClass'].value_counts().idxmax()
    top_pct   = d['GradeClass'].value_counts(normalize=True).max() * 100
    highlights.append({
        'label': 'Most Common Grade',
        'value': f"Grade {top_grade}",
        'detail': f"{top_pct:.1f}% of students in this segment",
        'tag': 'info'
    })

    # 4. A-grade students
    a_pct = (d['GradeClass'] == 'A').mean() * 100
    highlights.append({
        'label': 'Grade A Students',
        'value': f"{a_pct:.1f}%",
        'detail': f"{int(a_pct * len(d) / 100)} students achieving top grade",
        'tag': 'up' if a_pct >= 20 else 'neutral'
    })

    # 5. Study time vs GPA correlation
    corr = d[['StudyTimeWeekly', 'GPA']].corr().iloc[0, 1]
    avg_study = d['StudyTimeWeekly'].mean()
    highlights.append({
        'label': 'Study Time & GPA',
        'value': f"{avg_study:.1f} hrs/wk avg",
        'detail': f"Correlation with GPA: {corr:+.2f} ({'strong' if abs(corr) > 0.5 else 'moderate' if abs(corr) > 0.3 else 'weak'} positive link)",
        'tag': 'up' if corr > 0.3 else 'neutral'
    })

    # 6. Absences vs GPA
    avg_abs = d['Absences'].mean()
    abs_corr = d[['Absences', 'GPA']].corr().iloc[0, 1]
    highlights.append({
        'label': 'Absences',
        'value': f"{avg_abs:.1f} avg days",
        'detail': f"Correlation with GPA: {abs_corr:+.2f} — more absences {'hurts' if abs_corr < -0.2 else 'slightly affects'} grades",
        'tag': 'down' if abs_corr < -0.2 else 'neutral'
    })

    # 7. Best parental education group
    edu_gpa = d.groupby('ParentalEducation')['GPA'].mean().reindex(EDU_ORDER).dropna()
    if not edu_gpa.empty:
        best_edu = edu_gpa.idxmax()
        highlights.append({
            'label': 'Best Parental Education Level',
            'value': best_edu,
            'detail': f"Avg GPA {edu_gpa[best_edu]:.2f} — highest among all education groups",
            'tag': 'up'
        })

    # 8. Parental support impact
    sup_gpa = d.groupby('ParentalSupport')['GPA'].mean().reindex(SUP_ORDER).dropna()
    if len(sup_gpa) >= 2:
        gpa_range = sup_gpa.max() - sup_gpa.min()
        best_sup  = sup_gpa.idxmax()
        highlights.append({
            'label': 'Parental Support Impact',
            'value': f"{gpa_range:+.2f} GPA spread",
            'detail': f"'{best_sup}' support yields highest avg GPA ({sup_gpa[best_sup]:.2f})",
            'tag': 'up' if gpa_range > 0.3 else 'neutral'
        })

    # 9. Tutoring effect
    tut_yes = d[d['Tutoring'] == 'Yes']['GPA'].mean()
    tut_no  = d[d['Tutoring'] == 'No']['GPA'].mean()
    if pd.notna(tut_yes) and pd.notna(tut_no):
        diff = tut_yes - tut_no
        highlights.append({
            'label': 'Tutoring Effect',
            'value': f"{diff:+.2f} GPA",
            'detail': f"Tutored: {tut_yes:.2f} vs Non-tutored: {tut_no:.2f}",
            'tag': 'up' if diff > 0 else 'down'
        })

    # 10. Activity with biggest GPA boost
    activities = ['Extracurricular', 'Sports', 'Music', 'Volunteering']
    best_act, best_lift = None, -999
    for act in activities:
        yes_gpa = d[d[act] == 'Yes']['GPA'].mean()
        no_gpa  = d[d[act] == 'No']['GPA'].mean()
        if pd.notna(yes_gpa) and pd.notna(no_gpa):
            lift = yes_gpa - no_gpa
            if lift > best_lift:
                best_lift, best_act = lift, act
    if best_act:
        highlights.append({
            'label': 'Top Activity Boost',
            'value': best_act,
            'detail': f"Participants score {best_lift:+.2f} GPA vs non-participants",
            'tag': 'up' if best_lift > 0 else 'neutral'
        })

    return highlights

# ── Routes ────────────────────────────────────────────────────────────────────
@app.route('/')
def index():
    genders     = ['All'] + sorted(DF['Gender'].dropna().unique().tolist())
    ethnicities = ['All'] + sorted(DF['Ethnicity'].dropna().unique().tolist())
    grades      = ['All'] + [g for g in GRADE_ORDER if g in DF['GradeClass'].values]
    edus        = ['All'] + [e for e in EDU_ORDER if e in DF['ParentalEducation'].values]
    return render_template('index.html',
                           genders=genders, ethnicities=ethnicities,
                           grades=grades, edus=edus)

@app.route('/update', methods=['POST'])
def update():
    data = request.json
    d    = filter_df(data['gender'], data['ethnicity'], data['grade'], data['edu'])
    return jsonify({'highlights': build_highlights(d)})

if __name__ == '__main__':
    app.run(debug=True)
