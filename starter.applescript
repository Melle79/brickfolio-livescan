-- Startet den Live-Scanner ohne sichtbares Terminal.
-- Über start.sh, weil das Python aus macOS ein zu altes Tk mitbringt und
-- nur ein weisses Fenster zeichnen wuerde. start.sh sucht ein taugliches.
with timeout of 86400 seconds
	try
		do shell script "/bin/sh /Users/nutzer/dev/brickfolio-livescan/start.sh"
	on error meldung number nummer
		if nummer is not -128 then
			display dialog "Live-Scanner beendet:" & return & return & meldung ¬
				buttons {"OK"} default button 1 with icon caution
		end if
	end try
end timeout
