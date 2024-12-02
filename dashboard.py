import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import gspread
from read_json import response_json

# Настройка страницы
st.set_page_config(layout="wide")

# Добавляем CSS стили
st.markdown("""
    <style>
        .metric-container {
            background-color: #f0f2f6;
            border-radius: 10px;
            padding: 15px;
            margin: 5px;
            box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
        }
        .metric-label {
            color: #0f1b2a;
            font-size: 14px;
            font-weight: 500;
        }
        .metric-value {
            color: #1f77b4;
            font-size: 24px;
            font-weight: bold;
        }
        .branch-card {
            background-color: white;
            border-radius: 10px;
            padding: 20px;
            margin: 10px 0;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            transition: transform 0.2s;
        }
        .branch-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 6px 12px rgba(0, 0, 0, 0.15);
        }
        .branch-name {
            font-size: 20px;
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 15px;
            border-bottom: 2px solid #e0e0e0;
            padding-bottom: 5px;
        }
        .stats-container {
            display: flex;
            justify-content: space-between;
            margin-bottom: 10px;
        }
        .stat-item {
            text-align: center;
            flex: 1;
            padding: 0 10px;
        }
        .stat-value {
            font-size: 24px;
            font-weight: bold;
            margin-bottom: 5px;
        }
        .stat-label {
            font-size: 12px;
            color: #666;
        }
        .approved {
            color: #28a745;
        }
        .rejected {
            color: #dc3545;
        }
        .total {
            color: #17a2b8;
        }
        .approval-rate {
            color: #6f42c1;
        }
    </style>
""", unsafe_allow_html=True)

# Определяем цветовую схему
COLOR_SCHEME = {
    "Одобрено": "#28a745",
    "Отказано": "#dc3545"
}

def get_scoring_data():
    """Получение данных из Google Sheets"""
    try:
        response_ = response_json()
        sa = gspread.service_account_from_dict(response_)

        sh = sa.open("KreditMarket")
        worksheet = sh.worksheet("Scoring")

        data = worksheet.get_all_records()
        df = pd.DataFrame(data)

        # Проверяем формат даты и времени в данных
        print("Sample date from data:", df['Дата'].iloc[0] if not df.empty else "No data")

        # Принудительно преобразуем строки даты в datetime
        try:
            # Пробуем стандартный формат
            df['Дата'] = pd.to_datetime(df['Дата'], format='%Y-%m-%d %H:%M:%S')
        except:
            try:
                # Если не получилось, пробуем альтернативный формат
                df['Дата'] = pd.to_datetime(df['Дата'], format='%d.%m.%Y %H:%M:%S')
            except:
                # Если и это не сработало, пробуем автоматическое определение формата
                df['Дата'] = pd.to_datetime(df['Дата'], infer_datetime_format=True)

        # Проверяем успешность преобразования
        if not pd.api.types.is_datetime64_any_dtype(df['Дата']):
            raise ValueError("Failed to convert date column to datetime")

        return df
    except Exception as e:
        st.error(f"Ошибка при загрузке данных: {str(e)}")
        st.error("Пример формата даты из данных: " + str(df['Дата'].iloc[0] if not df.empty else "Нет данных"))
        raise e

def get_status_metrics(data):
    """Расчет метрик по статусам"""
    total = len(data)
    approved = len(data[data['Результат'] == 'Одобрено'])
    rejected = len(data[data['Результат'] == 'Отказано'])
    approval_rate = (approved / total * 100) if total > 0 else 0

    return {
        'total': total,
        'approved': approved,
        'rejected': rejected,
        'approval_rate': approval_rate
    }

def create_status_pie_chart(data):
    """Создание круговой диаграммы"""
    status_counts = data['Результат'].value_counts()
    fig = px.pie(
        values=status_counts.values,
        names=status_counts.index,
        title="Распределение статусов заявок",
        color_discrete_map=COLOR_SCHEME
    )
    return fig

def create_bar_chart(data, x_column, title):
    """Создание столбчатой диаграммы"""
    status_data = pd.crosstab(data[x_column], data['Результат'])
    fig = px.bar(
        status_data,
        barmode='group',
        title=title,
        color_discrete_map=COLOR_SCHEME
    )
    return fig

def create_time_series(data):
    """Создание графика временного ряда"""
    daily_status = data.groupby([data['Дата'].dt.date, 'Результат']).size().unstack(fill_value=0)
    fig = px.line(
        daily_status,
        title="Динамика заявок по дням",
        color_discrete_map=COLOR_SCHEME
    )
    return fig

def display_branch_cards(data, title):
    st.subheader(title)
    if len(data) == 0:
        st.info(f"Нет данных {title.lower()}")
        return

    for branch in data['Филиал'].unique():
        branch_data = data[data['Филиал'] == branch]
        metrics = get_status_metrics(branch_data)

        st.markdown(f"""
            <div class="branch-card">
                <div class="branch-name">{branch}</div>
                <div class="stats-container">
                    <div class="stat-item">
                        <div class="stat-value total">{metrics['total']}</div>
                        <div class="stat-label">ВСЕГО ЗАЯВОК</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value approved">{metrics['approved']}</div>
                        <div class="stat-label">ОДОБРЕНО</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value rejected">{metrics['rejected']}</div>
                        <div class="stat-label">ОТКАЗАНО</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value approval-rate">{metrics['approval_rate']:.1f}%</div>
                        <div class="stat-label">ПРОЦЕНТ ОДОБРЕНИЯ</div>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)

def main():
    st.markdown('<div class="main-header"><h1>Дашборд скоринга Kredit Market</h1></div>', unsafe_allow_html=True)

    try:
        # Получаем данные
        df = get_scoring_data()

        # Определяем временные периоды
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)

        # Создаем фильтры для разных периодов
        today_data = df[df['Дата'].dt.date == today]
        yesterday_data = df[df['Дата'].dt.date == yesterday]
        week_data = df[df['Дата'].dt.date >= week_ago]
        month_data = df[df['Дата'].dt.date >= month_ago]

        # Получаем метрики
        metrics_data = {
            "Сегодня": get_status_metrics(today_data),
            "Вчера": get_status_metrics(yesterday_data),
            "За неделю": get_status_metrics(week_data),
            "За месяц": get_status_metrics(month_data)
        }

        # Отображаем метрики в 4 колонках
        cols = st.columns(4)
        for col, (period, metrics) in zip(cols, metrics_data.items()):
            with col:
                st.markdown(f"""
                    <div class="metric-container">
                        <h3>{period}</h3>
                        <div class="metric-value">Всего: {metrics['total']}</div>
                        <div style="color: {COLOR_SCHEME['Одобрено']}">Одобрено: {metrics['approved']}</div>
                        <div style="color: {COLOR_SCHEME['Отказано']}">Отказано: {metrics['rejected']}</div>
                        <div class="metric-label">Процент одобрения: {metrics['approval_rate']:.1f}%</div>
                    </div>
                """, unsafe_allow_html=True)

        # Графики
        st.markdown("<hr>", unsafe_allow_html=True)

        # Добавляем селектор периода
        col_period_selector, _ = st.columns([1, 3])
        with col_period_selector:
            period = st.radio(
                "Период статистики:",
                ["За месяц", "За неделю"],
                horizontal=True,
                key="period_selector"
            )

        selected_data = month_data if period == "За месяц" else week_data
        period_suffix = "за месяц" if period == "За месяц" else "за неделю"

        col_left, col_right = st.columns(2)

        with col_left:
            st.plotly_chart(create_status_pie_chart(selected_data), use_container_width=True)
            st.plotly_chart(create_bar_chart(selected_data, 'Менеджер',
                                           f"Статистика по менеджерам {period_suffix}"), use_container_width=True)

        with col_right:
            st.plotly_chart(create_bar_chart(selected_data, 'Филиал',
                                           f"Статистика по филиалам {period_suffix}"), use_container_width=True)
            st.plotly_chart(create_time_series(selected_data), use_container_width=True)


        # Добавляем детальную статистику по филиалам за сегодня и вчера
        st.markdown("<hr>", unsafe_allow_html=True)
        col1, col2 = st.columns(2)

        with col1:
            display_branch_cards(today_data, "Статистика по филиалам за сегодня")

        with col2:
            display_branch_cards(yesterday_data, "Статистика по филиалам за вчера")

        # Добавляем сравнительный анализ
        st.markdown("<hr>", unsafe_allow_html=True)
        st.subheader("Сравнение с предыдущим днем")

        for branch in set(today_data['Филиал'].unique()) | set(yesterday_data['Филиал'].unique()):
            today_metrics = get_status_metrics(today_data[today_data['Филиал'] == branch])
            yesterday_metrics = get_status_metrics(yesterday_data[yesterday_data['Филиал'] == branch])

            change = today_metrics['total'] - yesterday_metrics['total']
            change_color = 'green' if change > 0 else 'red' if change < 0 else '#666'
            change_symbol = '↑' if change > 0 else '↓' if change < 0 else '='

            st.markdown(f"""
                <div class="branch-card">
                    <div class="branch-name">{branch}</div>
                    <div class="stats-container">
                        <div class="stat-item">
                            <div class="stat-value total">{today_metrics['total']}</div>
                            <div class="stat-label">СЕГОДНЯ (ВСЕГО)</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-value total">{yesterday_metrics['total']}</div>
                            <div class="stat-label">ВЧЕРА (ВСЕГО)</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-value" style="color: {change_color}">{change_symbol} {abs(change)}</div>
                            <div class="stat-label">ИЗМЕНЕНИЕ</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-value approval-rate">{today_metrics['approval_rate']:.1f}%</div>
                            <div class="stat-label">СЕГОДНЯ (% ОДОБРЕНИЯ)</div>
                        </div>
                        <div class="stat-item">
                            <div class="stat-value approval-rate">{yesterday_metrics['approval_rate']:.1f}%</div>
                            <div class="stat-label">ВЧЕРА (% ОДОБРЕНИЯ)</div>
                        </div>
                    </div>
                </div>
            """, unsafe_allow_html=True)
         # Детальная статистика по филиалам
        st.markdown("<hr>", unsafe_allow_html=True)
        st.subheader(f"Детальная статистика по филиалам {period_suffix}")

        branch_stats = pd.DataFrame()
        for branch in selected_data['Филиал'].unique():
            branch_data = selected_data[selected_data['Филиал'] == branch]
            metrics = get_status_metrics(branch_data)
            branch_stats = pd.concat([branch_stats, pd.DataFrame({
                'Филиал': [branch],
                'Всего заявок': [metrics['total']],
                'Одобрено': [metrics['approved']],
                'Отказано': [metrics['rejected']],
                'Процент одобрения': [f"{metrics['approval_rate']:.1f}%"]
            })])

        # Сбрасываем индекс и убеждаемся в уникальности
        branch_stats = branch_stats.reset_index(drop=True)

        # Проверяем на дубликаты и удаляем их если есть
        branch_stats = branch_stats.drop_duplicates()

        def highlight_stats(val):
            if isinstance(val, str) and '%' in val:
                rate = float(val.replace('%', ''))
                if rate >= 70:
                    return 'background-color: #d4edda; color: #155724'
                elif rate >= 50:
                    return 'background-color: #fff3cd; color: #856404'
                else:
                    return 'background-color: #f8d7da; color: #721c24'
            return ''

        st.dataframe(
            branch_stats.style
            .apply(lambda x: ['background-color: #f8f9fa' if i % 2 == 0 else '' for i in range(len(x))], axis=0)
            .applymap(highlight_stats)
            .set_properties(**{
                'text-align': 'center',
                'font-size': '14px',
                'padding': '10px'
            }),
            use_container_width=True,
            height=400
        )

    except Exception as e:
        st.error(f"Произошла ошибка при загрузке данных: {str(e)}")
        st.error("Пожалуйста, проверьте подключение к Google Sheets и формат данных.")

if __name__ == "__main__":
    main()
