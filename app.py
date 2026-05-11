# Wind Peak/Valley Labels with Arrows
    for d_date in df['date_only'].unique():
        day_block = df[(df['date_only'] == d_date) & (~df['is_night'])]
        if not day_block.empty:
            # PEAK
            peak = day_block.loc[day_block['wind'].idxmax()]
            # Horizontal Text Label
            fig_bot.add_annotation(
                x=peak['time'], y=peak['wind'], 
                text=f"<b>{round(peak['wind'])} kn</b>", 
                showarrow=False, yshift=15, xshift=-10,
                font=dict(size=10, color="white"), row=2, col=1
            )
            # Rotating Arrow only
            fig_bot.add_annotation(
                x=peak['time'], y=peak['wind'], 
                text="➤", textangle=peak['dir']-90, 
                showarrow=False, yshift=15, xshift=20,
                font=dict(size=10, color="white"), row=2, col=1
            )
            
            # VALLEY
            valley = day_block.loc[day_block['wind'].idxmin()]
            # Horizontal Text Label
            fig_bot.add_annotation(
                x=valley['time'], y=valley['wind'], 
                text=f"<b>{round(valley['wind'])} kn</b>", 
                showarrow=False, yshift=-15, xshift=-10,
                font=dict(size=10, color="#d1d9e0"), row=2, col=1
            )
            # Rotating Arrow only
            fig_bot.add_annotation(
                x=valley['time'], y=valley['wind'], 
                text="➤", textangle=valley['dir']-90, 
                showarrow=False, yshift=-15, xshift=20,
                font=dict(size=10, color="#d1d9e0"), row=2, col=1
            )

    # ... in fig_bot.update_layout ...
    xaxis2=dict(
        showticklabels=True, 
        tickmode='array', 
        tickvals=tick_vals, 
        ticktext=tick_text, # These are already wrapped in <b> tags above
        showgrid=True, 
        gridcolor="rgba(255,255,255,0.08)", 
        tickfont=dict(size=11, color="white")
    )
