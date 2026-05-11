# --- 2. BOTTOM GRAPHS (Segments, Wind, Tide) ---
    fig_bot = make_subplots(
        rows=3, cols=1, 
        shared_xaxes=True, 
        vertical_spacing=0.07, # Increased spacing to fit the day labels
        row_heights=[0.1, 0.6, 0.3]
    )
    
    # ... [Keep segments and wind line code the same as previous] ...
    # (Including segments loop, wind line loop, and tide trace here)

    # Segments
    heat_blocks = []
    for i in range(len(sun_data)):
        day_start, day_end = sun_data.iloc[i]['sunrise'], sun_data.iloc[i]['sunset']
        day_step = (day_end - day_start) / 3
        for s in range(3):
            t0, t1 = day_start + s*day_step, day_start + (s+1)*day_step
            mask = (df['time'] >= t0) & (df['time'] < t1)
            if not df[mask].empty:
                heat_blocks.append({'time': t0, 'end': t1, 'wind': df[mask]['wind'].mean(), 'dir': df[mask]['dir'].mean(), 'is_night': False})
        if i < len(sun_data) - 1:
            night_start, night_end = day_end, sun_data.iloc[i+1]['sunrise']
            night_step = (night_end - night_start) / 3
            for s in range(3):
                t0, t1 = night_start + s*night_step, night_start + (s+1)*night_step
                mask = (df['time'] >= t0) & (df['time'] < t1)
                if not df[mask].empty:
                    heat_blocks.append({'time': t0, 'end': t1, 'wind': df[mask]['wind'].mean(), 'dir': df[mask]['dir'].mean(), 'is_night': True})

    for b in heat_blocks:
        block_color = "#2c3e50" if b['is_night'] else get_color(b['wind'])
        mid_point = b['time'] + (b['end'] - b['time']) / 2
        width_ms = (b['end'] - b['time']).total_seconds() * 1000
        fig_bot.add_trace(go.Bar(
            x=[mid_point], y=[1], width=width_ms, 
            marker_color=block_color, showlegend=False, hoverinfo='none'
        ), row=1, col=1)
        fig_bot.add_annotation(x=mid_point, y=0.5, yref="y1", text="➤", textangle=b['dir']-90, showarrow=False, font=dict(size=14, color="white" if not b['is_night'] else "rgba(255,255,255,0.15)"), row=1, col=1)

    for i in range(len(df)-1):
        p1, p2 = df.iloc[i], df.iloc[i+1]
        op = 0.2 if (p1['is_night'] and p2['is_night']) else 1.0
        fig_bot.add_trace(go.Scatter(
            x=[p1['time'], p2['time']], y=[p1['wind'], p2['wind']], 
            mode='lines', line=dict(color=get_color(p1['wind'], opacity=op), width=2.5), 
            showlegend=False, hoverinfo='none'
        ), row=2, col=1)

    fig_bot.add_trace(go.Scatter(
        x=tide_df['time'], y=tide_df['height'],
        fill='tozeroy', mode='lines',
        line=dict(color='#5dade2', width=1.5),
        fillcolor='rgba(93, 173, 226, 0.15)',
        showlegend=False, hoverinfo='none'
    ), row=3, col=1)

    # Night Shading (Across all rows)
    for i in range(len(sun_data)-1):
        fig_bot.add_vrect(x0=sun_data['sunset'].iloc[i], x1=sun_data['sunrise'].iloc[i+1], fillcolor="#2c3e50", opacity=0.35, line_width=0, row="all")

    # Time Labels and Axis Config
    tick_vals = [pd.to_datetime(d) + timedelta(hours=12) for d in df['date_only'].unique()]
    tick_text = [pd.to_datetime(d).strftime('%a') for d in df['date_only'].unique()]

    fig_bot.update_layout(
        height=600, margin=dict(t=10, b=10, l=5, r=5), 
        template="plotly_dark", paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        yaxis1=dict(showticklabels=False, range=[0, 1], showgrid=False, zeroline=False),
        yaxis2=dict(showticklabels=False, showgrid=True, gridcolor="rgba(255,255,255,0.05)", zeroline=False),
        yaxis3=dict(showticklabels=False, showgrid=False, zeroline=False),
        # Labels explicitly on xaxis2 (under wind graph)
        xaxis1=dict(showticklabels=False),
        xaxis2=dict(
            showticklabels=True, 
            tickmode='array', 
            tickvals=tick_vals, 
            ticktext=tick_text, 
            showgrid=True, 
            gridcolor="rgba(255,255,255,0.08)", 
            tickfont=dict(size=12, family="Arial Black", color="white"),
            side='bottom'
        ),
        xaxis3=dict(showticklabels=False, showgrid=False)
    )

    st.plotly_chart(fig_bot, use_container_width=True, config={'displayModeBar': False})
