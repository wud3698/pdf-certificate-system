import pymysql

def check_db():
    # 连接到 MySQL 数据库
    conn = pymysql.connect(
        host='192.168.68.202',
        user='123456',
        password='123456',
        database='123456'
    )
    cursor = conn.cursor()
    
    # 获取表结构
    cursor.execute("DESCRIBE certificate")
    columns = cursor.fetchall()
    
    print("\n表结构：")
    for col in columns:
        print(f"{col[0]} ({col[1]})")
    
    # 获取总记录数
    cursor.execute("SELECT COUNT(*) FROM certificate")
    count = cursor.fetchone()[0]
    print(f"\n总记录数: {count}")
    
    if count > 0:
        # 获取所有记录
        cursor.execute("SELECT id, cert_number, unit_name, phone FROM certificate")
        records = cursor.fetchall()
        
        print("\n记录详情：")
        for record in records:
            print(f"ID: {record[0]}, 证书号: {record[1]}, 单位: {record[2]}, 电话: {record[3]}")
    
    conn.close()

if __name__ == '__main__':
    check_db() 