import os
import smtplib, ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


class EmailService:
    """
     Class for sending emails to multiple recipients.
    """

    def __init__(self, *args, **kwargs):
        """
        Sends the email to all recipients.
        :param kwargs:
           receivers (list): A list of dictionaries, each containing information about a recipient.
                Each dictionary should have the following keys:
                - email (str): The email address of the recipient.
                - full_name (str): The full name of the recipient.
        """

        self.smtp_port = os.environ.get('SMTP_PORT', 587)
        self.smtp_server = os.environ.get('SMTP_SERVER')
        self.smtp_sender_email = os.environ.get('SMTP_SENDER_EMAIL')
        self.smtp_username = os.environ.get('SMTP_USERNAME')
        self.smtp_password = os.environ.get('SMTP_PASSWORD')
        self.base_url = os.environ.get('BASE_URL')
        self.receivers = kwargs.get('receivers', [])

    def send_email(self):
        subject = "Push notification Token has Expired"
        html_content_template = '''
          <!DOCTYPE html>
              <html lang="en">
              <head>
                  <meta charset="UTF-8">
                  <meta name="viewport" content="width=device-width, initial-scale=1.0">
                  <title>Action Required: Push notification Token has Expired</title>
                  <style>
                      body {{
                          font-family: "Montserrat",serif;
                          line-height: 1.6;
                          margin: 0;
                          padding: 0;
                      }}

                      .container {{
                          max-width: 600px;
                          margin: auto;
                          padding: 20px;
                      }}


                      .content {{
                          padding: 0 20px 20px;
                          margin-top: -20px;
                      }}
                      ul {{
                          margin-top: -8px;
                      }}

                      a{{
                          text-decoration:none;
                          color: RGB(31,139,139);
                          font-family: "Montserrat",serif
                      }}

                      img{{
                          margin-left: -40px;
                      }}
                      .footer{{
                          margin-top: 30px;
                      }}
                  </style>
              </head>
              <body>
              <div class="container">
                  <div class="header">
                      <img src="{logo_image}" alt="Aegix Logo">
                  </div>
                  <div class="content">
                      <section>
                          <p>Attention {receiver_full_name},</p>
                          <p>Aegix is no longer able to send notifications to your {device} phone/tablet. As such, you may not be
                          notified of in-progress alerts.</p>
                          <p>To restore notifications, please follow these steps:</p>
                          <ul>
                              <li>Open <a href="{base_url}">Aegix AlM</a> on your {device} phone/tablet.</li>
                              <li>If you have been signed out, (a) enter your username & password, and (b)
                                  press the Sign-in button.
                              </li>
                          </ul>
                          <p>This will restore your push notifications from <b>Aegix AIM</b>. Please contact support with any issues
                              or questions.</p>
                      </section>
                      <section class="footer">
                          <div>Thank you for your attention to this matter, <br/>
                              Aegix Support <br/>
                              Mail: <a href="mailto:support@aegix.co">support@aegix.co</a> <br/>
                              Phone: <a href="tel:8886910699">888.691.0699</a></div>
                      </section>
                  </div>
              </div>
              </body>
              </html>
                      '''

        context = ssl.create_default_context()
        self.base_url = f"https://{self.base_url}"
        logo_image = f'{self.base_url}/img/aegix-logo.png'
        for receiver in self.receivers:
            receiver_email = receiver.get('email')
            receiver_full_name = receiver.get('full_name', 'Aegix AIM User')
            device = receiver.get('platform')
            message = MIMEMultipart()
            message["From"] = self.smtp_sender_email
            message["To"] = receiver_email
            message["Subject"] = subject
            html_content = html_content_template.format(receiver_full_name=receiver_full_name, device=device,
                                                        logo_image=logo_image, base_url=self.base_url)
            message.attach(MIMEText(html_content, "html"))
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                try:
                    server.starttls(context=context)
                    server.login(self.smtp_username, self.smtp_password)
                    server.sendmail(self.smtp_sender_email, receiver_email, message.as_string())
                    print(f"Email sent successfully to {receiver_email}")
                except Exception as e:
                    print(str(e))
