# Wind Peak/Valley Labels with Tightened Spacing
    for d_date in df['date_only'].unique():
        day_block = df[(df['date_only'] == d_date) & (~df['is_night'])]
        if not day_block.empty:
            # --- PEAK ---
            peak = day_block.loc[day_block['wind'].idxmax()]
            # Horizontal Number (shifted slightly left of center)
            fig_bot.add_annotation(
                x=peak['time'], y=peak['wind'], 
                text=f"<b>{round(peak['wind'])}</b>", 
                showarrow=False, yshift=15, xshift=-7,
                font=dict(size=10, color="white"), row=2, col=1
            )
            # Rotating Arrow (shifted slightly right of center to be close)
            fig_bot.add_annotation(
                x=peak['time'], y=peak['wind'], 
                text="➤", textangle=peak['dir']-90, 
                showarrow=False, yshift=15, xshift=10,
                font=dict(size=10, color="white"), row=2, col=1
            )
            
            # --- VALLEY ---
            valley = day_block.loc[day_block['wind'].idxmin()]
            # Horizontal Number
            fig_bot.add_annotation(
                x=valley['time'], y=valley['wind'], 
                text=f"<b>{round(valley['wind'])}</b>", 
                showarrow=False, yshift=-15, xshift=-7,
                font=dict(size=10, color="#d1d9e0"), row=2, col=1
            )
            # Rotating Arrow
            fig_bot.add_annotation(
                x=valley['time'], y=valley['wind'], 
                text="➤", textangle=valley['dir']-90, 
                showarrow=False, yshift=-15, xshift=10,
                font=dict(size=10, color="#d1d9e0"), row=2, col=1
            )
