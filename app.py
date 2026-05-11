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
        # Added explicit grid/line removal here
        xaxis=dict(showticklabels=False, showgrid=False, zeroline=False), 
        yaxis=dict(showticklabels=False, range=[0, 1.4], showgrid=False, zeroline=False)
    )
    st.plotly_chart(fig_top, use_container_width=True, config={'displayModeBar': False})
