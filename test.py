import smtplib
smtp=smtplib.SMTP('mail.clarkson.edu')
smtp.sendmail('printer@cslabs.clarkson.edu','beadleha@clarkson.edu','y')
