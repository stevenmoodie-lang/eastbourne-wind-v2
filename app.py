# --- HEADER ---
    idx_now = (df['time'] - now_nz).abs().idxmin()
    col1, col2 = st.columns([6, 1]) 
    with col1:
        st.markdown(f"<h1>Eastbourne Wind: {round(df.loc[idx_now, 'wind'])} kn</h1>", unsafe_allow_html=True)
        st.markdown(f"<div class='subtitle'>Monitoring at <b>{selection}</b> — Currently <b>{get_direction_label(df.loc[idx_now, 'dir'])}</b></div>", unsafe_allow_html=True)
    with col2:
        if st.button("🔄 Refresh"):
            st.cache_data.clear()
            st.rerun()

    # --- 1. TOP SUMMARY ---
    day_df = df[~df['is_night']].copy()
    daily_summary = day_df.groupby('date_only').agg({'wind': 'mean', 'dir': lambda x: x.mode()[0]}).reset_index()
    
    fig_top = go.Figure()
    fig_top.add_trace(go.Bar(
        x=daily_summary['date_only'].astype(str), y=[1]*len(daily_summary), 
        marker_color=[get_color(w) for w in daily_summary['wind']], 
        showlegend=False, hoverinfo='none'
    ))

    for i, row in daily_summary.iterrows():
        date_label = pd.to_datetime(row['date_only']).strftime('%a')
        fig_top.add_annotation(x=str(row['date_only']), y=1.22, text=f"<b>{date_label}</b>", showarrow=False, font=dict(size=11, color="white"))
        fig_top.add_annotation(x=str(row['date_only']), y=0.6, text=f"<b>{round(row['wind'])} kn</b>", showarrow=False, font=dict(size=13, color="white"))
        fig_top.add_annotation(
            x=str(row['date_only']), y=0.2, 
            text="➤", textangle=row['dir']-90,
            showarrow=False, font=dict(size=12, color="rgba(255,255,255,0.8)")
        )

    fig_top.update_layout(
        height=110, margin=dict(t=35, b=0, l=5, r=5), 
        template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        bargap=0.05, 
        xaxis=dict(showticklabels=False, showgrid=False, zeroline=False), 
        yaxis=dict(showticklabels=False, range=[0, 1.4], showgrid=False, zeroline=False)
    )
    st.plotly_chart(fig_top, use_container_width=True, config={'displayModeBar': False})

    # --- 2. BOTTOM GRAPH ---
    fig_bot = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.12, 0.88])
    
    # ROW 1: 4-Hourly Heatstrip
    df_4h = df.resample('4h', on='time', origin='start_day').agg({
        'wind': 'mean', 
        'dir': 'mean',
        'is_night': lambda x: x.mode()[0] 
    }).reset_index()
    
    for _, row in df_4h.iterrows():
        block_color = "#2c3e50" if row['is_night'] else get_color(row['wind'])
        arrow_color = "rgba(255,255,255,0.15)" if row['is_night'] else "white"

        fig_bot.add_trace(go.Bar(
            x=[row['time'] + timedelta(hours=2)], y=[1], width=1000*3600*4,
            marker_color=block_color, showlegend=False, hoverinfo='none'
        ), row=1, col=1)
        
        fig_bot.add_annotation(
            x=row['time'] + timedelta(hours=2), y=0.5, yref="y1",
            text="➤", textangle=row['dir']-90,
            showarrow=False, font=dict(size=14, color=arrow_color), row=1, col=1
        )

    # ROW 2: Wind Speed Line
    for i in range(len(df)-1):
        p1, p2 = df.iloc[i], df.iloc[i+1]
        opacity = 0.2 if (p1['is_night'] and p2['is_night']) else 1.0
        fig_bot.add_trace(go.Scatter(
            x=[p1['time'], p2['time']], y=[p1['wind'], p2['wind']], 
            mode='lines', line=dict(color=get_color(p1['wind'], opacity=opacity), width=2.5), 
            showlegend=False, hoverinfo='none'
        ), row=2, col=1)

    # Night Shading
    for i in range(len(sun_data)-1):
        fig_bot.add_vrect(x0=sun_data['sunset'].iloc[i], x1=sun_data['sunrise'].iloc[i+1], fillcolor="#2c3e50", opacity=0.4, line_width=0, row="all")
    
    # PEAK & VALLEY (Daylight Only)
    for d_date in df['date_only'].unique():
        day_block = df[(df['date_only'] == d_date) & (~df['is_night'])]
        if not day_block.empty:
            peak = day_block.loc[day_block['wind'].idxmax()]
            fig_bot.add_annotation(x=peak['time'], y=peak['wind'], text=f"<b>{round(peak['wind'])}</b>", 
                                   showarrow=False, yshift=15, font=dict(size=10, color="white"), row=2, col=1)
            valley = day_block.loc[day_block['wind'].idxmin()]
            fig_bot.add_annotation(x=valley['time'], y=valley['wind'], text=f"<b>{round(valley['wind'])}</b>", 
                                   showarrow=False, yshift=-15, font=dict(size=10, color="#d1d9e0"), row=2, col=1)

    tick_vals = [pd.to_datetime(d) + timedelta(hours=12) for d in df['date_only'].unique()]
    tick_text = [pd.to_datetime(d).strftime('%a') for d in df['date_only'].unique()]

    fig_bot.update_layout(
        height=380, margin=dict(t=10, b=0, l=5, r=5), 
        template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        yaxis1=dict(showticklabels=False, range=[0, 1], showgrid=False),
        yaxis2=dict(showticklabels=False, title=None, side="left", showgrid=True, gridcolor="rgba(255,255,255,0.08)"),
        xaxis2=dict(tickmode='array', tickvals=tick_vals, ticktext=tick_text, showgrid=True, gridcolor="rgba(255,255,255,0.08)", tickfont=dict(size=11, color="white", family="Arial Black"))
    )

    st.plotly_chart(fig_bot, use_container_width=True, config={'displayModeBar': False})

else:
    st.error("Error loading data")
